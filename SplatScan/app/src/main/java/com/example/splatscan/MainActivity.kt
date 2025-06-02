package com.example.splatscan

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.widget.Button
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.*
import android.app.AlertDialog
import android.widget.EditText
import android.graphics.Color
import java.util.concurrent.TimeUnit

import android.view.View
import android.widget.ProgressBar
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okio.BufferedSink


class MainActivity : AppCompatActivity() {

    private lateinit var startRecordingButton: Button
    private lateinit var uploadButton: Button

    private val REQUEST_VIDEO_CAPTURE = 1
    private var videoFile: File? = null
    private var videoUri: Uri? = null

    private var videoUploadParams: Map<String, String>? = null
    private var urlPart = "splatscan777scapp777" // Default zrok URL part
    private var isUploading: Boolean = false // Upload status tracker

    private lateinit var uploadProgressBar: ProgressBar
    private lateinit var generatingLayout: View


    // Runtime permission request launcher
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val cameraGranted = permissions[Manifest.permission.CAMERA] ?: false
        val micGranted = permissions[Manifest.permission.RECORD_AUDIO] ?: false
        if (cameraGranted && micGranted) {
            startRecordingButton.isEnabled = true
        } else {
            Toast.makeText(this, "Permissions not granted!", Toast.LENGTH_SHORT).show()
        }
    }

    // Dialog to input zrok subdomain
    private fun showUrlInputDialog() {
        val input = EditText(this)
        input.hint = "e.g., my1custom1reserved1zrok1url"
        input.setTextColor(Color.WHITE)

        val dialog = AlertDialog.Builder(this)
            .setTitle("Input URL")
            .setMessage("Input only the name of your reserved zrok URL")
            .setView(input)
            .setPositiveButton("save") { dialog, _ ->
                val enteredText = input.text.toString().trim()
                if (enteredText.isNotEmpty()) {
                    urlPart = enteredText
                    Toast.makeText(
                        this,
                        "Set URL to: https://$urlPart.share.zrok.io/upload",
                        Toast.LENGTH_SHORT
                    ).show()
                } else {
                    Toast.makeText(this, "No input", Toast.LENGTH_SHORT).show()
                }
                dialog.dismiss()
            }
            .setNegativeButton("cancel", null)
            .show()

        dialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(Color.WHITE)
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(Color.WHITE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Clear old video files on app start
        clearAppInternalVideoStorage()

        generatingLayout = findViewById(R.id.generatingLayout)


        startRecordingButton = findViewById(R.id.startRecordingButton)
        uploadButton = findViewById(R.id.uploadButton)
        uploadProgressBar = findViewById(R.id.uploadProgressBar)
        val setUrlButton = findViewById<Button>(R.id.setUrlButton)
        val parameterButton = findViewById<Button>(R.id.parameterButton)

        // Open zrok URL input dialog
        setUrlButton.setOnClickListener {
            showUrlInputDialog()
        }

        // Check permissions
        if (
            ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissionLauncher.launch(
                arrayOf(
                    Manifest.permission.CAMERA,
                    Manifest.permission.RECORD_AUDIO
                )
            )
        } else {
            startRecordingButton.isEnabled = true
        }

        // Start video recording
        startRecordingButton.setOnClickListener {
            dispatchTakeVideoIntent()
        }

        // Upload logic with upload state feedback
        uploadButton.setOnClickListener {
            if (isUploading) {
                Toast.makeText(this, "Another video is being uploaded. Please wait...", Toast.LENGTH_SHORT).show()
            } else {
                checkServerStatusAndUpload()
            }
        }

        // Show parameter input dialog
        parameterButton.setOnClickListener {
            showParameterDialog()
        }

        uploadButton.isEnabled = false // Enabled only after successful recording
    }

    // Delete all existing .mp4 files from app directory
    private fun clearAppInternalVideoStorage() {
        val dir = getExternalFilesDir(null)
        dir?.listFiles()?.forEach { file ->
            if (file.name.endsWith(".mp4")) {
                file.delete()
            }
        }
    }

    // Launch camera intent to record video
    private fun dispatchTakeVideoIntent() {
        val intent = Intent(MediaStore.ACTION_VIDEO_CAPTURE)
        intent.putExtra(MediaStore.EXTRA_DURATION_LIMIT, 3600) // Max 1 hour

        videoFile = createVideoFile()
        videoUri = FileProvider.getUriForFile(this, "$packageName.fileprovider", videoFile!!)
        intent.putExtra(MediaStore.EXTRA_OUTPUT, videoUri)

        startActivityForResult(intent, REQUEST_VIDEO_CAPTURE)
    }

    // Create a unique video file in the app's directory
    private fun createVideoFile(): File {
        val timeStamp: String = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val fileName = "VID_$timeStamp.mp4"
        return File(getExternalFilesDir(null), fileName)
    }

    // Handle video recording result
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_VIDEO_CAPTURE && resultCode == Activity.RESULT_OK) {
            Toast.makeText(this, "Video recorded!!", Toast.LENGTH_SHORT).show()
            uploadButton.isEnabled = true
        } else {
            Toast.makeText(this, "Recording cancelled", Toast.LENGTH_SHORT).show()
        }
    }

    private fun startPollingJobStatus() {
        Thread {
            while (true) {
                try {
                    val statusUrl = "https://$urlPart.share.zrok.io/status"
                    val request = Request.Builder().url(statusUrl).get().build()
                    val client = OkHttpClient()
                    val response = client.newCall(request).execute()
                    val body = response.body?.string() ?: ""

                    if (response.isSuccessful && body.contains("idle")) {
                        runOnUiThread {
                            generatingLayout.visibility = View.GONE // Spinner ausblenden
                            Toast.makeText(this, "Finished splat, hurray!", Toast.LENGTH_SHORT).show()
                        }
                        break // Beende die Schleife, Job fertig
                    }

                    Thread.sleep(5000) // 5 Sekunden warten bis nächster Check
                } catch (e: Exception) {
                    e.printStackTrace()
                    break
                }
            }
        }.start()
    }


    // Upload video file to server via HTTP POST
    private fun uploadVideo() {
        uploadProgressBar.progress = 0
        uploadProgressBar.visibility = View.VISIBLE

        Thread {
            try {
                val videoRequestBody = object : RequestBody() {
                    override fun contentType() = "video/mp4".toMediaTypeOrNull()

                    override fun contentLength(): Long = videoFile!!.length()

                    override fun writeTo(sink: BufferedSink) {
                        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                        val input = videoFile!!.inputStream()
                        var uploaded: Long = 0
                        input.use {
                            var read: Int
                            while (input.read(buffer).also { read = it } != -1) {
                                sink.write(buffer, 0, read)
                                uploaded += read

                                val progress = (100 * uploaded / contentLength()).toInt()
                                runOnUiThread {
                                    uploadProgressBar.progress = progress
                                }
                            }
                        }
                    }
                }

                val builder = MultipartBody.Builder().setType(MultipartBody.FORM)
                builder.addFormDataPart("video", videoFile!!.name, videoRequestBody)

                // Parameter hinzufügen
                videoUploadParams?.forEach { (key, value) ->
                    builder.addFormDataPart(key, value)
                }

                val requestBody = builder.build()
                val fullUrl = "https://$urlPart.share.zrok.io/upload"

                val request = Request.Builder()
                    .url(fullUrl)
                    .post(requestBody)
                    .build()

                val client = OkHttpClient.Builder()
                    .connectTimeout(60, TimeUnit.SECONDS)
                    .writeTimeout(15, TimeUnit.MINUTES)
                    .readTimeout(15, TimeUnit.MINUTES)
                    .build()

                val response = client.newCall(request).execute()

                runOnUiThread {
                    uploadProgressBar.visibility = View.GONE
                    isUploading = false
                    when (response.code) {
                        200 -> {
                            generatingLayout.visibility = View.VISIBLE // Spinner zeigen
                            Toast.makeText(this, "Upload successful, job started!", Toast.LENGTH_SHORT).show()
                            startPollingJobStatus() // Polling starten, Jobstatus abfragen
                        }
                        429 -> Toast.makeText(this, "Another video is being processed please wait", Toast.LENGTH_LONG).show()
                        else -> Toast.makeText(this, "Upload failed: ${response.code}", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
                runOnUiThread {
                    isUploading = false
                    uploadProgressBar.visibility = View.GONE
                    Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    private fun checkServerStatusAndUpload() {
        val fullStatusUrl = "https://$urlPart.share.zrok.io/status"

        Thread {
            try {
                val request = Request.Builder().url(fullStatusUrl).get().build()
                val client = OkHttpClient()
                val response = client.newCall(request).execute()
                val responseBody = response.body?.string()

                runOnUiThread {
                    if (response.isSuccessful && responseBody?.contains("idle") == true) {
                        Toast.makeText(this, "Upload started...", Toast.LENGTH_SHORT).show()
                        isUploading = true
                        uploadVideo()
                    } else {
                        Toast.makeText(this, "Another video is being processed please wait...", Toast.LENGTH_LONG).show()
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    Toast.makeText(this, "Error while status check: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }


    // Show dialog for custom training parameters
    private fun showParameterDialog() {
        val dialogView = layoutInflater.inflate(R.layout.dialog_parameters, null)

        val iterationsInput = dialogView.findViewById<EditText>(R.id.iterationsInput)
        val keepPreInput = dialogView.findViewById<EditText>(R.id.keepPreInput)
        val keepPostInput = dialogView.findViewById<EditText>(R.id.keepPostInput)
        val imagesInput = dialogView.findViewById<EditText>(R.id.imagesInput)

        val dialog = AlertDialog.Builder(this)
            .setTitle("Training Parameters")
            .setView(dialogView)
            .setPositiveButton("Save") { _, _ ->
                val iterations = iterationsInput.text.toString()
                val keepPre = keepPreInput.text.toString()
                val keepPost = keepPostInput.text.toString()
                val keepTrainImages = imagesInput.text.toString()

                videoUploadParams = mapOf(
                    "iterations" to iterations,
                    "keep_pre" to keepPre,
                    "keep_post" to keepPost,
                    "keep_train_images" to keepTrainImages
                )

                dialogView.postDelayed({
                    Toast.makeText(this, "Parameters saved", Toast.LENGTH_SHORT).show()
                }, 300)
            }
            .setNegativeButton("Cancel", null)
            .show()

        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setTextColor(Color.WHITE)
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setTextColor(Color.WHITE)
    }
}
