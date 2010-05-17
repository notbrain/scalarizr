#!/bin/sh
#
# scalarizr - this script starts and stops the scalarizr daemon
#
# chkconfig:   235 85 15
# description:  Scalarizr is a part of Scalr project
# processname: scalarizr
# config:      /etc/scalarizr/config.ini
# config:      /etc/sysconfig/scalarizr
# pidfile:     /var/run/scalarizr.pid

# Source function library.
. /etc/rc.d/init.d/functions

# Source networking configuration.
. /etc/sysconfig/network

# Check that networking is up.
[ "$NETWORKING" = "no" ] && exit 0

scalarizr="/usr/bin/scalarizr"
prog=$(basename $scalarizr)

SCALARIZR_CONF_FILE="/etc/scalarizr/config.ini"

[ -f /etc/sysconfig/scalarizr ] && . /etc/sysconfig/scalarizr

lockfile=/var/lock/subsys/scalarizr
scripts_path=$(cat $SCALARIZR_CONF_FILE | grep "scripts_path" | awk '{print $3}')

start() {
    [ -x $scalarizr ] || exit 5
    [ -f $SCALARIZR_CONF_FILE ] || exit 6
    echo -n $"Starting $prog: "
    daemon $scalarizr -c $SCALARIZR_CONF_FILE
    retval=$?
    echo
    [ $retval -eq 0 ] && touch $lockfile
    return $retval
}

stop() {
    echo -n $"Stopping $prog: "
	run_level=$(who -r | awk '{print $2}')
	if [ $run_level == "0" ]; then
		$scripts_path/halt
	elif [ $run_level == "6" ]; then
		$scripts_path/reboot
	fi    
    killproc $prog
    retval=$?
    echo
    [ $retval -eq 0 ] && rm -f $lockfile
    return $retval
}

restart() {
    stop
    start
}

reload() {
    echo -n $"Reloading $prog: "
    killproc $scalarizr -HUP
    echo
}

rh_status() {
    status $prog
}

rh_status_q() {
    rh_status >/dev/null 2>&1
}


case "$1" in
    start)
        rh_status_q && exit 0
        $1
        ;;
    stop)
        rh_status_q || exit 0
        $1
        ;;
    restart)
        $1
        ;;
    force-reload|upgrade) 
        rh_status_q || exit 7
        upgrade
        ;;
    reload)
        rh_status_q || exit 7
        $1
        ;;
    status|status_q)
        rh_$1
        ;;
    condrestart|try-restart)
        rh_status_q || exit 7
        restart
	    ;;
    *)
        echo $"Usage: $0 {start|stop|reload|status|force-reload|restart}"
        exit 2
esac

