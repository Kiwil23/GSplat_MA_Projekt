# syntax=docker/dockerfile:1
ARG UBUNTU_VERSION=22.04
ARG NVIDIA_CUDA_VERSION=11.8.0
# CUDA architectures, required by Colmap and tiny-cuda-nn. Use >= 8.0 for faster TCNN.
ARG CUDA_ARCHITECTURES="90;75"
ARG NERFSTUDIO_VERSION=""

# Pull source either provided or from git.
FROM scratch as source_copy
ONBUILD COPY . /tmp/nerfstudio
FROM alpine/git as source_no_copy
ARG NERFSTUDIO_VERSION=""
ONBUILD RUN git clone --branch ${NERFSTUDIO_VERSION} --recursive https://github.com/nerfstudio-project/nerfstudio.git /tmp/nerfstudio
ARG NERFSTUDIO_VERSION
FROM source_${NERFSTUDIO_VERSION:+no_}copy as source

FROM nvidia/cuda:${NVIDIA_CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} as builder
ARG CUDA_ARCHITECTURES
ARG NVIDIA_CUDA_VERSION
ARG UBUNTU_VERSION

ENV CMAKE_BUILD_PARALLEL_LEVEL=4
ENV DEBIAN_FRONTEND=noninteractive
ENV QT_XCB_GL_INTEGRATION=xcb_egl
RUN apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        git \
        wget \
        ninja-build \
        build-essential \
        libboost-program-options-dev \
        libboost-filesystem-dev \
        libboost-graph-dev \
        libboost-system-dev \
        libeigen3-dev \
        libflann-dev \
        libfreeimage-dev \
        libmetis-dev \
        libgoogle-glog-dev \
        libgtest-dev \
        libsqlite3-dev \
        libglew-dev \
        qtbase5-dev \
        libqt5opengl5-dev \
        libcgal-dev \
        libceres-dev \
        python3.10-dev \
        python3-pip &&\
      

        # Upgrade pip and install dependencies.
        # pip install torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cu118 && \
        pip install  --upgrade pip 'setuptools<70.0.0' && \
        pip install  --upgrade pip numpy==1.26.4 scipy==1.11.4 && \
        pip install  torch==2.1.2+cu118 torchvision==0.16.2+cu118 --extra-index-url https://download.pytorch.org/whl/cu118 &&\
        git clone --branch master --recursive https://github.com/cvg/Hierarchical-Localization.git /opt/hloc && \
        cd /opt/hloc && git checkout v1.4 && python3.10 -m pip install  . && cd ~ && \
        MAX_JOBS=1 TCNN_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" pip install  "git+https://github.com/NVlabs/tiny-cuda-nn.git@b3473c81396fe927293bdfd5a6be32df8769927c#subdirectory=bindings/torch" && \
        pip install  pycolmap==0.6.1 pyceres==2.1 omegaconf==2.3.0 &&\
# Build and install CMake
        wget https://github.com/Kitware/CMake/releases/download/v3.31.3/cmake-3.31.3-linux-x86_64.sh \
        -q -O /tmp/cmake-install.sh \
        && chmod u+x /tmp/cmake-install.sh \
        && mkdir /opt/cmake-3.31.3 \
        && /tmp/cmake-install.sh --skip-license --prefix=/opt/cmake-3.31.3 \
        && rm /tmp/cmake-install.sh \
        && ln -s /opt/cmake-3.31.3/bin/* /usr/local/bin 



  
    
# Install gsplat and nerfstudio.
# NOTE: both are installed jointly in order to prevent docker cache with latest
# gsplat version (we do not expliticly specify the commit hash).
#
# We set MAX_JOBS to reduce resource usage for GH actions:
# - https://github.com/nerfstudio-project/gsplat/blob/db444b904976d6e01e79b736dd89a1070b0ee1d0/setup.py#L13-L23
COPY --from=source /tmp/nerfstudio/ /tmp/nerfstudio
RUN export TORCH_CUDA_ARCH_LIST="$(echo "$CUDA_ARCHITECTURES" | tr ';' '\n' | awk '$0 > 70 {print substr($0,1,1)"."substr($0,2)}' | tr '\n' ' ' | sed 's/ $//')" && \
    export MAX_JOBS=4 && \
    GSPLAT_VERSION="$(sed -n 's/.*gsplat==\s*\([^," '"'"']*\).*/\1/p' /tmp/nerfstudio/pyproject.toml)" && \
    pip install  git+https://github.com/nerfstudio-project/gsplat.git@v${GSPLAT_VERSION} && \
    pip install  /tmp/nerfstudio 'numpy<2.0.0' && \
    rm -rf /tmp/nerfstudio &&\


    # Build and install COLMAP.
    git clone https://github.com/colmap/colmap.git && \
    cd colmap && \
    git checkout "3.9.1" && \
    mkdir build && \
    cd build && \
    mkdir -p /build && \
    cmake .. -GNinja "-DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES}" \
        -DCMAKE_INSTALL_PREFIX=/build/colmap && \
    ninja install -j1 && \
    cd ~ && \

    # Fix permissions
    chmod -R go=u /usr/local/lib/python3.10 && \
    chmod -R go=u /build &&\

    find /usr/local/lib/python3.10/dist-packages/ -type d -name '__pycache__' -exec rm -rf {} + && \
    find /usr/local/lib/python3.10/dist-packages/ -type f -name '*.py[co]' -delete

#
# Docker runtime stage.
#
FROM nvidia/cuda:${NVIDIA_CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION} as runtime
ARG CUDA_ARCHITECTURES
ARG NVIDIA_CUDA_VERSION
ARG UBUNTU_VERSION

LABEL org.opencontainers.image.source = "https://github.com/nerfstudio-project/nerfstudio"
LABEL org.opencontainers.image.licenses = "Apache License 2.0"
LABEL org.opencontainers.image.base.name="docker.io/library/nvidia/cuda:${NVIDIA_CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION}"
LABEL org.opencontainers.image.documentation = "https://docs.nerf.studio/"


# Minimal dependencies to run COLMAP binary compiled in the builder stage.
# Note: this reduces the size of the final image considerably, since all the
# build dependencies are not needed.
RUN apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        libboost-filesystem1.74.0 \
        libboost-program-options1.74.0 \
        libc6 \
        libceres2 \
        libfreeimage3 \
        libgcc-s1 \
        libgl1 \
        libglew2.2 \
        libgoogle-glog0v5 \
        libqt5core5a \
        libqt5gui5 \
        libqt5widgets5 \
        python3.10 \
        python3.10-dev \
        build-essential \
        python-is-python3 \
        python3-pip \
        ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \

 # Installiere Python-Abhängigkeiten mit pip
    pip install --no-cache-dir \
    opencv-python \
    open3d \
    pycolmap \
    numpy==1.26.4 \
    scipy==1.11.4 

# Copy packages from builder stage.
COPY --from=builder /build/colmap/ /usr/local/ 
COPY --from=builder /usr/local/lib/python3.10/dist-packages/ /usr/local/lib/python3.10/dist-packages/ 
COPY --from=builder /usr/local/bin/ns* /usr/local/bin/ 

WORKDIR /custom_Modules 
COPY read_write_model.py /custom_Modules/read_write_model.py 

ENV PYTHONPATH="/custom_Modules:${PYTHONPATH}" 

# Bash as default entrypoint.
CMD /bin/bash -l