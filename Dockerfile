FROM ovishpc/ldms-dev:latest
# --- Base tooling & build deps (PAPI + cyPAPI + OVIS) ---
RUN apt-get update && \
   DEBIAN_FRONTEND=noninteractive apt-get install -y \
     build-essential git pkg-config autoconf automake libtool \
     python3-dev python3-setuptools python3-pip \
     wget ca-certificates && \
   rm -rf /var/lib/apt/lists/*
# --- Build & install PAPI 7.1.0 ---
WORKDIR /tmp
RUN wget https://icl.utk.edu/projects/papi/downloads/papi-7.1.0.tar.gz && \
   tar -xzf papi-7.1.0.tar.gz && \
   cd papi-7.1.0/src && \
   ./configure --prefix=/usr/local && \
   make -j"$(nproc)" && \
   make install && \
   ldconfig && \
   cd / && rm -rf /tmp/papi-7.1.0 /tmp/papi-7.1.0.tar.gz
# --- Install cyPAPI (Python bindings for PAPI) ---
WORKDIR /root
RUN python3 -m pip install -U pip setuptools wheel "cython>=3.0.0" build && \
   git clone https://github.com/icl-utk-edu/cyPAPI.git && \
   cd cyPAPI && \
   make install
# --- Build & install OVIS/LDMS from source into /opt/ovis ---
WORKDIR /root
RUN git clone https://github.com/ovis-hpc/ovis.git && \
   cd ovis && \
   ./autogen.sh && \
   mkdir build && cd build && \
   ../configure --prefix=/opt/ovis && \
   make -j"$(nproc)" && \
   make install
# --- Paths for runtime ---
ENV PATH="/opt/ovis/bin:/usr/local/bin:${PATH}" \
   LD_LIBRARY_PATH="/opt/ovis/lib:/usr/local/lib:${LD_LIBRARY_PATH}"
# Keep container alive for interactive work / testing
CMD ["bash","-lc","sleep infinity"]
