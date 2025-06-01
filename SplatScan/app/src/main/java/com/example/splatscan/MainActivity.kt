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

class MainActivity : AppCompatActivity() {

    private lateinit var startRecordingButton: Button
    private lateinit var uploadButton: Button

    private val REQUEST_VIDEO_CAPTURE = 1
    private var videoFile: File? = null
    private var videoUri: Uri? = null

    private var videoUploadParams: Map<String, String>? = null
    private var urlPart = "splatscan777scapp777" // Default zrok URL part
    private var isUploading: Boolean = false // Upload status tracker

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

        startRecordingButton = findViewById(R.id.startRecordingButton)
        uploadButton = findViewById(R.id.uploadButton)
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
                Toast.makeText(this, "Upload started...", Toast.LENGTH_SHORT).show()
                isUploading = true
                uploadVideo()
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

    // Upload video file to server via HTTP POST
    private fun uploadVideo() {
        Thread {
            try {
                val builder = MultipartBody.Builder().setType(MultipartBody.FORM)

                builder.addFormDataPart(
                    "video",
                    videoFile!!.name,
                    videoFile!!.asRequestBody("video/mp4".toMediaTypeOrNull())
                )

                // Add parameters if available
                videoUploadParams?.forEach { (key, value) ->
                    builder.addFormDataPart(key, value)
                }

                val requestBody = builder.build()
                val fullUrl = "https://$urlPart.share.zrok.io/upload"

                val request = Request.Builder()
                    .url(fullUrl)
                    .post(requestBody)
                    .build()

                val client = OkHttpClient()
                val response = client.newCall(request).execute()

                runOnUiThread {
                    isUploading = false
                    when (response.code) {
                        200 -> {
                            Toast.makeText(this, "Upload successful, job started", Toast.LENGTH_SHORT).show()
                        }
                        429 -> {
                            Toast.makeText(this, "Another video is being processed. Please wait...", Toast.LENGTH_LONG).show()
                        }
                        else -> {
                            Toast.makeText(this, "Upload failed: Error code ${response.code}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }

            } catch (e: IOException) {
                e.printStackTrace()
                runOnUiThread {
                    isUploading = false
                    Toast.makeText(this, "Error uploading: ${e.message}", Toast.LENGTH_LONG).show()
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
