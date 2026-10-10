# Linux 常用运维命令手册

## 一、系统信息查看

- 查看系统版本：`cat /etc/os-release`
- 查看内核版本：`uname -r`
- 查看 CPU 信息：`lscpu` 或 `cat /proc/cpuinfo`
- 查看内存信息：`free -h`
- 查看磁盘空间：`df -h`
- 查看目录占用：`du -sh <目录>`

## 二、进程管理

- 查看进程：`ps aux` 或 `top`
- 实时监控进程：`htop`
- 查找进程：`ps aux | grep <进程名>`
- 结束进程：`kill <PID>` 或 `kill -9 <PID>`
- 查看端口占用：`netstat -tunlp` 或 `ss -tunlp`

## 三、日志查看

- 实时查看日志：`tail -f <日志文件>`
- 查看最后 100 行：`tail -n 100 <日志文件>`
- 搜索日志关键字：`grep "error" <日志文件>`
- 查看系统日志：`journalctl -xe`

## 四、文件与权限

- 查看文件权限：`ls -l`
- 修改权限：`chmod 755 <文件>`
- 修改属主：`chown user:group <文件>`
- 查找文件：`find / -name "<文件名>"`
- 查看文件内容：`cat <文件>` 或 `less <文件>`

## 五、网络排查

- 测试网络连通：`ping <主机>`
- 测试端口连通：`telnet <主机> <端口>` 或 `nc -zv <主机> <端口>`
- 查看路由：`ip route`
- 查看 IP 地址：`ip addr`
- 抓包分析：`tcpdump -i <网卡>`
