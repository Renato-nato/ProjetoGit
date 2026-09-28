#!/bin/bash
# baixa um video do Pexels pelo ID, descobrindo o nome do arquivo (prefere vertical 1080x1920)
id=$1; UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
[ -s px_$id.mp4 ] && exit 0
for res in hd_1080_1920 uhd_2160_3840 hd_1080_2048 uhd_2160_4096 hd_1920_1080 uhd_3840_2160 hd_1280_720 hd_720_1280 uhd_2560_1440 hd_2048_1080 uhd_4096_2160 sd_540_960 sd_960_540; do
  for fps in 25 30 24 60 50 29 23; do
    u="https://videos.pexels.com/video-files/$id/$id-${res}_${fps}fps.mp4"
    if [ "$(curl -s -o /dev/null -w '%{http_code}' -A "$UA" -I "$u")" = "200" ]; then curl -sSL -A "$UA" -o px_$id.mp4 "$u"; echo "$id OK $res $fps"; exit 0; fi
  done
done
echo "$id NAO ACHADO"
