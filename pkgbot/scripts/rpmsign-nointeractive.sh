#!/usr/bin/expect -f

spawn rpm --addsign {*}$argv
expect -exact "Enter pass phrase: "
send -- "\r"
expect eof
