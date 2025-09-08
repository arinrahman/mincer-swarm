set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git build-essential autoconf automake libtool pkg-config gettext
cd /root
test -d ovis || git clone https://github.com/ovis-hpc/ovis.git
cd ovis
./autogen.sh
./configure --prefix=/opt/ovis
make -j"$(nproc)"
make install
echo 'export PATH=/opt/ovis/bin:$PATH' > /etc/profile.d/ldms.sh
echo "[OK] LDMS installed to /opt/ovis"
