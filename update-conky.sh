#/bin/sh

INFO='\e[38;05;14m'
NC='\033[0m' # No Color

# Status:
sudo systemctl status conky && ps -eo pid,vsz,rss,comm | grep -i python3 && free -m

echo "Shutting down conky..."
echo -e "${INFO}systemctl stop conky${NC}";
sudo systemctl stop conky
echo "Updating conky..."
echo -e "${INFO}git fetch${NC}";
sudo git fetch
echo -e "${INFO}git pull${NC}";
sudo git pull
echo "Starting up conky..."
echo -e "${INFO}systemctl start conky${NC}";
sudo systemctl start conky

sudo systemctl status conky && ps -eo pid,vsz,rss,comm | grep -i python3 && free -m
