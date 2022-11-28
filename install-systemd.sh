#/bin/sh

INFO='\e[38;05;14m'
NC='\033[0m' # No Color

echo -e "${INFO}cp ~/conky/conky.service /lib/systemd/system/${NC}";
sudo cp ~/conky/conky.service /lib/systemd/system/
echo -e "${INFO}systemctl enable conky${NC}";
sudo systemctl enable conky
echo -e "${INFO}systemctl daemon-reload${NC}";
sudo systemctl daemon-reload
echo -e "${INFO}systemctl start conky${NC}";
sudo systemctl start conky
echo -e "${INFO}systemctl status conky${NC}";
sudo systemctl status conky
