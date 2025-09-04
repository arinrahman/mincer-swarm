FROM ovishpc/ldms-dev:latest
# Add useful tools for your lab
RUN apt-get update && apt-get install -y \
   iproute2 iptables iputils-ping tcpdump iperf3 nmap \
   netcat-openbsd hping3 curl \
&& rm -rf /var/lib/apt/lists/*
# Keep container alive; you can `docker exec` in later
CMD ["bash","-lc","sleep infinity"]
