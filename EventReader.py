"""
EventReader - lê o chat do Roblox via OCR e avisa no Discord quando o evento aparece.

Uso:
    python EventReader.py            -> roda em loop até você apertar Ctrl+C
    python EventReader.py --teste    -> captura uma vez, salva janela.png/chat.png e mostra o texto lido
"""
import os
import sys
import time
import difflib
from ctypes import windll

import requests
import pytesseract
import win32gui
import win32ui
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# ---------------- Configuração ----------------
pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK", "").strip()
USER_ID = os.getenv("DISCORD_USER_ID", "").strip()


def _lista(nome, padrao):
    return [x.strip().lower() for x in os.getenv(nome, padrao).split(",") if x.strip()]


def _area(nome, padrao):
    try:
        v = tuple(int(x) for x in os.getenv(nome, padrao).split(","))
        assert len(v) == 4
        return v
    except Exception:
        raise SystemExit(f"{nome} inválido no .env. Use o formato: esquerda,topo,direita,base")


TITULO_JANELA = os.getenv("TITULO_JANELA", "Roblox")
PALAVRAS = _lista("PALAVRAS", "evento,boss,spawn")   # palavras que disparam o aviso
INTERVALO = 1.5        # segundos entre cada leitura
COOLDOWN = 30          # segundos mínimos entre dois avisos
ESQUECER_APOS = 300    # segundos até a mesma linha poder avisar de novo
SIMILARIDADE = 0.85    # evita avisar de novo por pequenas variações do OCR

# Área do chat DENTRO da janela do Roblox: esquerda,topo,direita,base
# Cada pessoa ajusta no .env (use --teste e confira o chat.png)
AREA_CHAT = _area("AREA_CHAT", "10,80,510,330")

try:  # evita recorte deslocado com escala do Windows (125%, 150%...)
    windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------- Captura ----------------
def capturar_janela(titulo=TITULO_JANELA):
    hwnd = win32gui.FindWindow(None, titulo)
    if not hwnd or win32gui.IsIconic(hwnd):  # não achou ou está minimizada
        return None

    l, t, r, b = win32gui.GetWindowRect(hwnd)
    w, h = r - l, b - t
    if w <= 0 or h <= 0:
        return None

    hwnd_dc = mfc_dc = save_dc = bmp = None
    try:
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bmp)

        windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)

        bits = bmp.GetBitmapBits(True)
        return Image.frombuffer("RGB", (w, h), bits, "raw", "BGRX", 0, 1)
    finally:  # sempre libera os recursos do Windows, mesmo se der erro
        if bmp is not None:
            win32gui.DeleteObject(bmp.GetHandle())
        if save_dc is not None:
            save_dc.DeleteDC()
        if mfc_dc is not None:
            mfc_dc.DeleteDC()
        if hwnd_dc is not None:
            win32gui.ReleaseDC(hwnd, hwnd_dc)


def ler_chat(img):
    chat = img.crop(AREA_CHAT).convert("L")
    chat = chat.resize((chat.width * 2, chat.height * 2))
    return pytesseract.image_to_string(chat).lower()


# ---------------- Discord ----------------
def avisar(texto):
    mencao = f"<@{USER_ID}> " if USER_ID else ""
    try:
        r = requests.post(
            WEBHOOK_URL,
            json={"content": f"{mencao}🚨 Evento detectado! `{texto[:100]}`"},
            timeout=10,
        )
        if r.status_code >= 400:
            log(f"Discord recusou o aviso (HTTP {r.status_code}). Confere o webhook.")
            return False
        return True
    except requests.RequestException as e:
        log(f"Falha ao enviar pro Discord: {e}")
        return False


def ja_avisado(linha, vistos):
    agora = time.time()
    for antiga in list(vistos):  # limpa linhas antigas
        if agora - vistos[antiga] > ESQUECER_APOS:
            del vistos[antiga]
    return any(difflib.SequenceMatcher(None, linha, v).ratio() >= SIMILARIDADE for v in vistos)


# ---------------- Modos ----------------
def modo_teste():
    img = capturar_janela()
    if not img:
        log("Janela do Roblox não encontrada (ou minimizada). Confere o título.")
        return
    img.save("janela.png")
    chat = img.crop(AREA_CHAT)
    chat.save("chat.png")
    log("Salvei janela.png e chat.png. Texto lido:")
    print(pytesseract.image_to_string(chat.convert("L")))


def modo_loop():
    if not WEBHOOK_URL or "cole_" in WEBHOOK_URL:
        log("DISCORD_WEBHOOK não configurado. Preencha o arquivo .env (veja .env.example).")
        sys.exit(1)

    log("Monitorando o chat. Aperte Ctrl+C para parar.")
    ultimo_aviso = 0
    vistos = {}      # linha -> momento em que avisou
    avisou_sem_janela = False

    while True:
        try:
            img = capturar_janela()
            if not img:
                if not avisou_sem_janela:
                    log("Janela do Roblox não encontrada. Aguardando...")
                    avisou_sem_janela = True
                time.sleep(2)
                continue
            avisou_sem_janela = False

            texto = ler_chat(img)
            achadas = [
                ln.strip() for ln in texto.splitlines()
                if ln.strip() and any(p in ln for p in PALAVRAS)
            ]
            novas = [ln for ln in achadas if not ja_avisado(ln, vistos)]

            if novas and time.time() - ultimo_aviso > COOLDOWN:
                if avisar(" | ".join(novas)):
                    log(f"Aviso enviado: {novas[0][:80]}")
                    ultimo_aviso = time.time()
                    for ln in novas:
                        vistos[ln] = time.time()

        except KeyboardInterrupt:
            raise
        except Exception as e:  # um erro isolado não derruba o loop
            log(f"Erro na leitura (continuando): {e}")
            time.sleep(3)

        time.sleep(INTERVALO)


if __name__ == "__main__":
    try:
        if "--teste" in sys.argv:
            modo_teste()
        else:
            modo_loop()
    except KeyboardInterrupt:
        log("Parado pelo usuário. Até mais!")
