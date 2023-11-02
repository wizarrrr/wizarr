#!/bin/bash

# Text colors
BLACK="\e[30m"
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
MAGENTA="\e[35m"
CYAN="\e[36m"
WHITE="\e[37m"

# Background colors
BGBLACK="\e[40m"
BGRED="\e[41m"
BGGREEN="\e[42m"
BGYELLOW="\e[43m"
BGBLUE="\e[44m"
BGMAGENTA="\e[45m"
BGCYAN="\e[46m"
BGWHITE="\e[47m"

# Text styles
BOLD="\e[1m"
DIM="\e[2m"
UNDERLINE="\e[4m"
BLINK="\e[5m"
INVERT="\e[7m"
HIDDEN="\e[8m"

# Reset to default
ENDCOLOR="\e[0m"

# Get OS version
. /etc/os-release

# Get latest version
WIZARR_VERSION=$(< /latest)
WIZARR_LATEST=$(curl -s --max-time 5 https://api.github.com/repos/wizarrrr/wizarr/releases/latest | grep tag_name | cut -d '"' -f 4 || echo "${WIZARR_VERSION}")
read -r WIZARR_VERSION_MIN _ <<< "$WIZARR_VERSION"

# Function to print a header
header_text() {
    local text="$1"
    local terminal_width=$(tput cols)  # Get the width of the terminal
    local text_width=$(toilet -f standard -F border -- "${text}" | wc -L)

    # Calculate the number of spaces needed to center the text
    local padding=$((($terminal_width - $text_width) / 2))

    # Create a line of spaces to use as padding
    local padding_line=""
    for ((i = 0; i < padding; i++)); do
        padding_line+=" "
    done

    # Print the centered text
    toilet -f standard -F border -- "${text}" | sed "s/^/${padding_line}/"
}

# Function to print centered text
center_text() {
    local text="$1"
    local terminal_width=$(tput cols)  # Get the width of the terminal
    text_no_ansi=$(echo -e -n "$text" | sed -r -e "s/\x1B\[[0-9;]*[mK]//g" -e "s/\\n//g")

    # Calculate the number of spaces needed to center the text
    local text_width=$(echo -e -n "$text_no_ansi" | wc -L)
    local padding=$((($terminal_width - $text_width) / 2))

    # Create a line of spaces to use as padding
    local padding_line=""
    for ((i = 0; i < padding; i++)); do
        padding_line+=" "
    done

    echo -e "${padding_line}${text}"
}

# Function to print a horizontal line
print_horizontal_line() {
    local terminal_width=$(tput cols)  # Get the width of the terminal
    local character="$1"               # The character to use for the line

    for ((i = 0; i < terminal_width; i++)); do
        printf "%s" "$character"
    done

    printf "\n"
}

# Function to create Wizarr Version Color
wizarr_version_color() {
    local version="$1"
    local latest="$2"
    local version_min="$3"
    local latest_min="$4"

    local colored_version

    if [[ "$version" == "$latest" ]]; then
        colored_version="${GREEN}${version}${ENDCOLOR}"
    elif [[ "$version_min" == "$latest_min" ]]; then
        colored_version="${YELLOW}${version}${ENDCOLOR}"
    else
        colored_version="${RED}${version}${ENDCOLOR}"
    fi

    echo -n "$colored_version"
}

# Function to print OUTDATED warning if Wizarr is outdated
wizarr_outdated_warning() {
    local version="$1"
    local latest="$2"
    local version_min="$3"
    local latest_min="$4"

    if [[ "$version" != "$latest" ]]; then
        center_text "${BGYELLOW} You are running version ${version} and the latest version is ${latest}. ${ENDCOLOR}"
    fi
}

WIZARR_COLORED_VERSION=$(wizarr_version_color "$WIZARR_VERSION" "$WIZARR_LATEST" "$WIZARR_VERSION_MIN" "$WIZARR_LATEST_MIN")

WIZARR_HEADER="Wizarr V${LATEST_MIN}"
WIZARR_SUBHEADER="${ENDCOLOR}Wizarr Version ${WIZARR_COLORED_VERSION} - OS Version ${MAGENTA}${PRETTY_NAME:-unknown}${ENDCOLOR}"

# Print the Wizarr
echo -e "${BOLD}${BLUE}"
header_text "  ${WIZARR_HEADER}  "
center_text "${ENDCOLOR}${WIZARR_SUBHEADER}\n"
wizarr_outdated_warning "$WIZARR_VERSION" "$WIZARR_LATEST" "$WIZARR_VERSION_MIN" "$WIZARR_LATEST_MIN"

