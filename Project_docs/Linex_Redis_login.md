Welcome to Ubuntu 24.04.1 LTS (GNU/Linux 5.15.167.4-microsoft-standard-WSL2 x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

 System information as of Sat Feb  1 05:57:23 UTC 2025

  System load:  0.34                Processes:             45
  Usage of /:   0.1% of 1006.85GB   Users logged in:       0
  Memory usage: 6%                  IPv4 address for eth0: 172.22.184.151
  Swap usage:   0%

  userid   viodkumarhs
  password  $VP@sdc2020$
The following additional packages will be installed:
  redis-server redis-tools

  vinodkumarhs@Vinodhome:~$ sudo service redis-server start
vinodkumarhs@Vinodhome:~$ redis-cli ping
PONG

vinodkumarhs@Vinodhome:~$ sudo service redis-server status    (server status)

 redis-server.service - Advanced key-value store
     Loaded: loaded (/usr/lib/systemd/system/redis-server.service; disabled; preset: enabled)
     Active: active (running) since Sat 2025-02-01 06:00:29 UTC; 12h ago
       Docs: http://redis.io/documentation,
             man:redis-server(1)
   Main PID: 887 (redis-server)
     Status: "Ready to accept connections"
      Tasks: 6 (limit: 9357)
     Memory: 8.7M ()
     CGroup: /system.slice/redis-server.service
             └─887 "/usr/bin/redis-server 127.0.0.1:6379"