#!/bin/bash

# 下記の接続情報を自分の環境に合わせて修正してください。
ATOMCAM_IP='192.168.2.110'
ATOMCAM_USER=root
ATOMCAM_PASS=atomcam2

WGET=`which wget`" -nc -r -nv -nH --cut-dir=3"

ATOMCAM_FTP="ftp://${ATOMCAM_USER}:${ATOMCAM_PASS}@${ATOMCAM_IP}/media/mmc/record"

if [ $# -ne 3 ] ; then
    echo "Usage: atom_ftp.sh yyyymmdd start_hour end_hour" 
    echo '  ex. atom_ftp.sh 20220104 1 2'
    exit 1
fi

DATE=$1

for hour in `seq $2 $3`
do
    hh=`printf "%02d\n" $hour`
    FTP_COMMAND="${WGET} ${ATOMCAM_FTP}/$DATE/$hh"
    echo $FTP_COMMAND
    $FTP_COMMAND
done



