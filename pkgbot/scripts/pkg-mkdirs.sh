#!/bin/bash

mkdir -p /var/run/aptly-spooler/

_CHK_USER=$(getent passwd mirror)
_CHK_GROUP=$(getent group mirror)
if [ ! -z ${_CHK_USER} ] && [ ! -z ${_CHK_GROUP} ]; then
  chown mirror:mirror /var/run/aptly-spooler/
else
  echo "WARNING: user/group mirror not found."
  echo "Please create them manually and set permissions with the following command:"
  echo "  chown mirror:mirror /var/run/aptly-spooler"
fi
