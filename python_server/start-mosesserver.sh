#!/bin/bash

mosesserver_cmd=${MOSES_ROOT}/bin/mosesserver 
mosesserver_config=${MOSES_MODELS}/moses.ini
mosesserver_port=${MOSES_PORT}
mosesserver_log=${MOSES_LOG}


if [ ${mosesserver_port} ] ; then if [ ${mosesserver_port} != '' ] ; then serverport_par="--server-port $mosesserver_port" ; fi ; fi

if [ ${mosesserver_log} ] ; then if [ ${mosesserver_log} != '' ] ; then serverlog_par="--server-log $mosesserver_log" ; fi ; fi

$mosesserver_cmd -f $mosesserver_config $serverport_par $serverlog_par

