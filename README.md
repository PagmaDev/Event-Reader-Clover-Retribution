# Event Reader

Lê o chat do Roblox via OCR e manda um alerta no seu Discord quando o evento/portal aparece.
Roda em loop até você parar com **Ctrl+C**.

## Como funciona
1. Captura a janela do Roblox (mesmo em segundo plano, mas não minimizada)
2. Recorta a área do chat e lê o texto com o Tesseract OCR
3. Se aparecer uma das palavras configuradas, envia um aviso pelo webhook do Discord
4. Não repete o aviso pra mesma mensagem e respeita um cooldown entre alertas

## Instalação (Windows)
1. Instale o [Python](https://www.python.org/downloads/) e o [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
2. Baixe o projeto e, na pasta dele: `pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e preencha **com os seus dados**:
   - `DISCORD_WEBHOOK`: o webhook do seu canal (obrigatório)
   - `DISCORD_USER_ID`: seu ID do Discord, se quiser ser mencionado (opcional)
4. Teste o webhook: `python teste.py`
5. Ajuste a área do chat: abra o Roblox, rode `python EventReader.py --teste` e confira o `chat.png`. Se o recorte estiver errado, mude `AREA_CHAT` no `.env`
6. Rode: `python EventReader.py` (Ctrl+C para parar)

## Problemas comuns
- **"Janela do Roblox não encontrada"**: confira `TITULO_JANELA` no `.env` e não deixe a janela minimizada
- **Recorte deslocado**: ajuste `AREA_CHAT` olhando o `janela.png` gerado pelo `--teste`
- **Texto lido errado**: ajuste a área do chat pra pegar só as mensagens, sem o fundo do jogo
- **Tesseract não encontrado**: defina `TESSERACT_PATH` no `.env`

## Segurança
Seu `.env` é só seu: ele está no `.gitignore` e nunca deve ser compartilhado ou enviado pro GitHub.
Se um webhook vazar, apague-o no Discord e crie outro.
