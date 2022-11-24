check version:

dmesg | grep MPTCP

change scheduler:

sudo sysctl -w net.mptcp.mptcp_scheduler=redundant
sudo sysctl -w net.mptcp.mptcp_scheduler=default
sudo sysctl -w net.mptcp.mptcp_scheduler=blest
sudo sysctl -w net.mptcp.mptcp_enabled=1

print current setting:

sudo sysctl -a | grep mptcp

change congestion control algorithm(CCA)

echo reno > /proc/sys/net/ipv4/tcp_congestion_control
echo cubic > /proc/sys/net/ipv4/tcp_congestion_control
echo bbr > /proc/sys/net/ipv4/tcp_congestion_control


print(CCA)
cat /proc/sys/net/ipv4/tcp_congestion_control