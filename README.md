# GitLab package bot

"The package bot" An simple service which receives HTTP build triggers from gitlab, gets the builded packages and puts them in aptly.


## Manual Installation
```
apt-get install python-yaml python-pip
pip install python-gitlab

git clone git@git.adfinis-sygroup.ch:ad-sy/gitlab-ci-pkg-bot.src.git
cd gitlab-ci-pkg-bot.src
python setup.py install
mkdir /var/run/aptly-spooler
chown mirror:mirror /var/run/aptly-spooler

```

## Configuration & Administration

### Configuration

Them main config file for PKGBOT is located at `/etc/gitlab-pkgbot.yaml`

### Administration

PKGBOT runs as systemd service. Its logs can be viewed with the following command:
```
systemctl status gitlab-pkgbot.service
```



## aptly-spooler

Since aptly can only run a command at once, this script sets up an simple
"spooler" for running all aptly commands.
This is implemented via an FIFO-Socket located at `/var/run/aptly-spooler/fifo.sock`. This socket accepts commands seperated by newlines and executes them one by one.

You can manually pipe commands in this spooler as well:

```
echo "sleep 10" > /var/run/aptly-spooler/fifo.sock
echo "ps fuax" > /var/run/aptly-spooler/fifo.sock
```

The spooler runs as systemd service, logs can be viewed via the following command:
```
systemctl status aptly-spooler.service
```


## mkdir
```
mkdir -p centos/{6,7} redhat/{6,7} debian/{jessie,wheezy} ubuntu/{trusty,vivid,xenial}mkdir -p centos/{6,7} rhel/{6,7} debian/{jessie,wheezy} ubuntu/{trusty,vivid,xenial}
```
