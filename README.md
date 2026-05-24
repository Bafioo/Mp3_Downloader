# MP3 Downloader

Script Python per cercare una lista di brani su YouTube e salvarli come MP3.
Usalo solo per contenuti che puoi scaricare legalmente.

## Requisiti

- Python 3.10 o superiore
- ffmpeg installato e disponibile nel PATH
- yt-dlp:

```powershell
python -m pip install -U -r requirements.txt
```

## Lista brani

Crea un file `songs.txt` nella cartella del progetto, con una canzone per riga:

```text
Artista - Titolo
Artista; Titolo
Artista | Titolo
```

Puoi usare `songs.txt.example` come traccia.

## Uso

Controlla prima le ricerche che verranno fatte:

```powershell
python .\mp3_download.py --dry-run
```

Scarica gli MP3 nella cartella `downloads`:

```powershell
python .\mp3_download.py
```

Usa un file o una cartella diversa:

```powershell
python .\mp3_download.py -i .\mia_lista.txt -o .\musica
```

Lo script crea `downloads\downloaded.txt` per evitare di riscaricare gli stessi video.
