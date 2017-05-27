# GitLab Package Bot

A simple service which receives HTTP build triggers from GitLab, gets the built
packages and puts them in aptly and RPM repos.

## Installation
```
# apt-get install python-yaml python-pip
# pip install python-gitlab
``` 

Clone this repository and switch into the directory:
```
# python setup.py install
# mkdir /var/run/aptly-spooler
# chown mirror:mirror /var/run/aptly-spooler
```

## Configuration & Administration

### Configuration

The main config file for the bot is located at `/etc/gitlab-pkgbot.yaml`.

### Administration

It runs as a systemd service. You can view logs with the following command:
```
# journalctl -u gitlab-pkgbot.service
```

## aptly-spooler

Since aptly can only run one command at once, this script sets up a simple
"spooler" for running all aptly commands.
This is implemented via a FIFO-Socket located at 
`/var/run/aptly-spooler/fifo.sock`. The socket accepts commands seperated by 
newlines and executes them one by one.

You can manually pipe commands into this spooler as well:

```
# echo "sleep 10" > /var/run/aptly-spooler/fifo.sock
# echo "ps -efH" > /var/run/aptly-spooler/fifo.sock
```

It runs as a systemd service. You can view logs with the following command:
```
# journalctl -u aptly-spooler.service
```

## Mirror preparation

The bot copies the extracted packages into a specific directory tree before
adding them to the specific repositories. Meaning the required directories have
to be created first:
```
# cd /path/to/your/mirror/dir
# mkdir -p centos/{6,7} redhat/{6,7} debian/{jessie,wheezy} \
  ubuntu/{trusty,vivid,xenial}mkdir -p centos/{6,7} rhel/{6,7}
# chown -R mirror:mirror /path/to/your/mirror/dir
```

## Contributions

Contributions are more than welcome! Please feel free to open new issues or
pull requests.

## License

GNU GENERAL PUBLIC LICENSE Version 3

See the [LICENSE](LICENSE) file.
