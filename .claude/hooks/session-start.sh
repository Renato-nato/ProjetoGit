#!/bin/bash
# Garante que o FFmpeg esteja disponível em toda sessão do Claude Code
# (web e local). Idempotente: se já estiver instalado, não faz nada.
# Nunca derruba a sessão: se não conseguir instalar, só avisa.
set -uo pipefail

if command -v ffmpeg >/dev/null 2>&1; then
  exit 0
fi

echo "FFmpeg não encontrado. Instalando..." >&2

# Roda como root direto, ou com sudo sem senha (não trava pedindo senha).
as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n "$@"
  else
    return 1
  fi
}

install_ffmpeg() {
  case "$(uname -s)" in
    Darwin)
      command -v brew >/dev/null 2>&1 && brew install ffmpeg
      ;;
    Linux)
      if command -v apt-get >/dev/null 2>&1; then
        as_root apt-get update -qq &&
          as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg
      elif command -v dnf >/dev/null 2>&1; then
        as_root dnf install -y ffmpeg
      elif command -v pacman >/dev/null 2>&1; then
        as_root pacman -S --noconfirm ffmpeg
      elif command -v apk >/dev/null 2>&1; then
        as_root apk add --no-cache ffmpeg
      else
        return 1
      fi
      ;;
    MINGW* | MSYS* | CYGWIN*)
      command -v winget >/dev/null 2>&1 &&
        winget install --id Gyan.FFmpeg -e --silent \
          --accept-package-agreements --accept-source-agreements
      ;;
    *)
      return 1
      ;;
  esac
}

if install_ffmpeg >/dev/null 2>&1 && command -v ffmpeg >/dev/null 2>&1; then
  echo "FFmpeg instalado: $(ffmpeg -version | head -1)" >&2
else
  echo "Não foi possível instalar o FFmpeg automaticamente." >&2
  echo "Instale manualmente: macOS 'brew install ffmpeg' | Ubuntu 'sudo apt install ffmpeg' | Windows 'winget install Gyan.FFmpeg'" >&2
fi

exit 0
