#!/bin/bash

# Aliases
alias l='ls -lAsh --color'
alias ls='ls -C1 --color'
alias cp='cp -ip'
alias rm='rm -i'
alias mv='mv -i'
alias h='cd ~;clear;'


IFS="."

. /etc/os-release
LATEST=`cat /data/latest`
read -r LATEST_MIN _ <<< "$LATEST"
NPM_BUILD_VERSION=$(npm --version)


IFS=" "

echo -e -n '\E[1;34m'
figlet -w 120 "        Wizarr V${LATEST_MIN}"
echo -e "\E[1;36mWizarr Version \E[1;32m${LATEST:-unknown} \E[1;36mNPM Version \E[1;32m${NPM_BUILD_VERSION:-unknown} \E[1;36mOS Version \E[1;32m${PRETTY_NAME:-unknown}"
echo -e '\E[0m'