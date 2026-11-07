"""
Minimal translation layer. English is the base language; Turkish is bundled.

Usage:  from core.i18n import tr, set_language
        tr("convert.button")            -> "Convert"
        tr("status.saved", path="x.mp3") -> "Saved: x.mp3"
"""
import locale

LANGUAGES = {"en": "English", "tr": "Türkçe"}

_current = "en"

STRINGS = {
    # ── App / header ───────────────────────────────────────────────────────
    "app.tagline": {"en": "Convert · Trim · Extract · Tag", "tr": "Dönüştür · Kes · Çıkar · Etiketle"},
    "app.language": {"en": "Language:", "tr": "Dil:"},
    "app.lang_busy": {"en": "Please wait until the current job finishes before changing the language.",
                      "tr": "Dili değiştirmeden önce lütfen süren işlemin bitmesini bekleyin."},
    "app.busy_title": {"en": "Busy", "tr": "Meşgul"},
    "app.drop_overlay": {"en": "Drop files or folders here", "tr": "Dosya veya klasörleri buraya bırakın"},
    "app.ffmpeg_missing": {
        "en": "FFmpeg was not found.\n\nPlace ffmpeg.exe and ffprobe.exe next to WaveSmith.exe, "
              "or install FFmpeg and add it to PATH:\nhttps://ffmpeg.org/download.html",
        "tr": "FFmpeg bulunamadı.\n\nffmpeg.exe ve ffprobe.exe dosyalarını WaveSmith.exe'nin yanına koyun "
              "ya da FFmpeg'i kurup PATH'e ekleyin:\nhttps://ffmpeg.org/download.html"},

    # ── Tabs ───────────────────────────────────────────────────────────────
    "tab.convert": {"en": "🔄  Convert", "tr": "🔄  Dönüştür"},
    "tab.trim": {"en": "✂  Trim && Fade", "tr": "✂  Kesme && Fade"},
    "tab.extract": {"en": "🎬  Extract from Video", "tr": "🎬  Videodan Ses Çıkar"},
    "tab.metadata": {"en": "🏷  Metadata", "tr": "🏷  Etiketler"},

    # ── File queue ─────────────────────────────────────────────────────────
    "queue.title": {"en": "📂  Files", "tr": "📂  Dosyalar"},
    "queue.title_video": {"en": "📂  Video Files", "tr": "📂  Video Dosyaları"},
    "queue.add_files": {"en": "Add Files…", "tr": "Dosya Ekle…"},
    "queue.add_folder": {"en": "Add Folder…", "tr": "Klasör Ekle…"},
    "queue.remove": {"en": "Remove", "tr": "Kaldır"},
    "queue.clear": {"en": "Clear", "tr": "Temizle"},
    "queue.edit_tags": {"en": "🏷  Edit Tags…", "tr": "🏷  Etiketleri Düzenle…"},
    "queue.subfolders": {"en": "Include subfolders", "tr": "Alt klasörleri dahil et"},
    "queue.hint": {"en": "Drag & drop files or folders here, or use the buttons above.",
                   "tr": "Dosya veya klasörleri buraya sürükleyip bırakın ya da yukarıdaki düğmeleri kullanın."},
    "queue.col_file": {"en": "File", "tr": "Dosya"},
    "queue.col_info": {"en": "Info", "tr": "Bilgi"},
    "queue.col_status": {"en": "Status", "tr": "Durum"},
    "queue.count": {"en": "{n} file(s)", "tr": "{n} dosya"},
    "queue.none_added": {"en": "No supported media files were found in what you dropped.",
                         "tr": "Bıraktıklarınız arasında desteklenen medya dosyası bulunamadı."},
    "queue.tags_edited": {"en": "tags edited", "tr": "etiket düzenlendi"},
    "info.video": {"en": "🎬 Video", "tr": "🎬 Video"},
    "info.audio": {"en": "🎵 Audio", "tr": "🎵 Ses"},
    "info.no_audio": {"en": "⚠ no audio", "tr": "⚠ ses yok"},
    "info.probing": {"en": "reading…", "tr": "okunuyor…"},

    # ── Single file picker ─────────────────────────────────────────────────
    "picker.title": {"en": "📂  Source File (video or audio)", "tr": "📂  Kaynak Dosya (Video veya Ses)"},
    "picker.choose": {"en": "Choose File…", "tr": "Dosya Seç…"},
    "picker.none": {"en": "No file selected — or drag & drop one here",
                    "tr": "Henüz dosya seçilmedi — ya da buraya sürükleyip bırakın"},
    "filter.all_media": {"en": "All media", "tr": "Tüm medya"},
    "filter.video": {"en": "Video", "tr": "Video"},
    "filter.audio": {"en": "Audio", "tr": "Ses"},
    "filter.images": {"en": "Images", "tr": "Görseller"},
    "dlg.choose_files": {"en": "Choose Files", "tr": "Dosya Seç"},
    "dlg.choose_folder": {"en": "Choose Folder", "tr": "Klasör Seç"},

    # ── Output dir ─────────────────────────────────────────────────────────
    "out.title": {"en": "📁  Output Folder", "tr": "📁  Çıktı Klasörü"},
    "out.choose": {"en": "Choose…", "tr": "Seç…"},
    "out.reset": {"en": "Reset", "tr": "Sıfırla"},
    "out.same": {"en": "Same folder as each source file", "tr": "Her kaynak dosya ile aynı klasör"},

    # ── Format / codec ─────────────────────────────────────────────────────
    "fmt.target": {"en": "🎵  Target Format", "tr": "🎵  Hedef Format"},
    "fmt.output": {"en": "🎵  Output Format", "tr": "🎵  Çıktı Formatı"},
    "fmt.format": {"en": "Format:", "tr": "Format:"},
    "codec.title": {"en": "⚙  Codec Settings", "tr": "⚙  Codec Ayarları"},
    "codec.reset": {"en": "↺  Reset to Recommended", "tr": "↺  Önerilen Ayarlara Sıfırla"},
    "codec.quality": {"en": "Quality (VBR):", "tr": "Kalite (VBR):"},
    "codec.quality_mp3": {"en": "  (0 = best)", "tr": "  (0 = en iyi)"},
    "codec.quality_ogg": {"en": "  (10 = best)", "tr": "  (10 = en iyi)"},
    "codec.bitrate": {"en": "Bitrate (CBR):", "tr": "Bit hızı (CBR):"},
    "codec.flac": {"en": "FLAC Compression:", "tr": "FLAC Sıkıştırma:"},
    "codec.flac_suffix": {"en": "  (0 = fast, 12 = small)", "tr": "  (0 = hızlı, 12 = küçük)"},
    "codec.sample_rate": {"en": "Sample Rate:", "tr": "Örnekleme Hızı:"},
    "codec.channels": {"en": "Channels:", "tr": "Kanal:"},
    "ch.stereo": {"en": "Stereo", "tr": "Stereo"},
    "ch.mono": {"en": "Mono", "tr": "Mono"},
    "ch.joint stereo": {"en": "Joint stereo", "tr": "Birleşik stereo"},
    "ch.5.1 surround": {"en": "5.1 surround", "tr": "5.1 çevresel ses"},
    "codec_desc.MP3": {"en": "Universal compatibility. Great for streaming & portable devices.",
                       "tr": "Her yerde çalışır. Akış ve taşınabilir cihazlar için ideal."},
    "codec_desc.AAC": {"en": "Apple's standard. Better quality than MP3 at the same bitrate.",
                       "tr": "Apple'ın standardı. Aynı bit hızında MP3'ten daha iyi kalite."},
    "codec_desc.OGG Vorbis": {"en": "Open source. Excellent quality/size ratio. Popular in games.",
                              "tr": "Açık kaynak. Kalite/boyut oranı çok iyi. Oyunlarda yaygın."},
    "codec_desc.OPUS": {"en": "Modern codec. Very good quality at low bitrates. Ideal for voice.",
                        "tr": "Modern codec. Düşük bit hızında çok iyi kalite. Konuşma için ideal."},
    "codec_desc.FLAC": {"en": "Lossless compression. No quality loss. Audiophile standard.",
                        "tr": "Kayıpsız sıkıştırma. Kalite kaybı yok. Audiofil standardı."},
    "codec_desc.WAV (PCM)": {"en": "Uncompressed raw audio. Maximum quality, large files.",
                             "tr": "Sıkıştırılmamış ham ses. En yüksek kalite, büyük dosya."},
    "codec_desc.AIFF": {"en": "Apple's uncompressed format. Studio-grade audio.",
                        "tr": "Apple'ın sıkıştırılmamış formatı. Stüdyo kalitesinde ses."},
    "codec_desc.WMA": {"en": "Windows Media Audio. Good compatibility in the Windows ecosystem.",
                       "tr": "Windows Media Audio. Windows ortamında iyi uyumluluk."},
    "codec_desc.AC3 (Dolby)": {"en": "Dolby Digital. Standard for DVDs and home theater systems.",
                               "tr": "Dolby Digital. DVD ve ev sinema sistemlerinin standardı."},
    "codec_desc.DTS": {"en": "Digital Theater Systems. High-bitrate surround for home theater / AVR.",
                       "tr": "Digital Theater Systems. Ev sineması / AVR için yüksek bit hızlı çevresel ses."},
    "codec_desc.MP2": {"en": "MPEG-1 Layer II. Used in broadcasting and professional environments.",
                       "tr": "MPEG-1 Layer II. Yayıncılık ve profesyonel ortamlarda kullanılır."},

    # ── Effects ────────────────────────────────────────────────────────────
    "fx.title": {"en": "✨  Post-Processing", "tr": "✨  Son İşlem"},
    "fx.fade_in": {"en": "Fade in", "tr": "Fade in (giriş)"},
    "fx.fade_out": {"en": "Fade out", "tr": "Fade out (çıkış)"},
    "fx.fade_len": {"en": "Fade length:", "tr": "Fade süresi:"},
    "fx.seconds": {"en": " s", "tr": " sn"},
    "fx.keep_cover": {"en": "Keep cover art (MP3 / FLAC / M4A output)",
                      "tr": "Kapak görselini koru (MP3 / FLAC / M4A çıktısı)"},

    # ── Trim tab ───────────────────────────────────────────────────────────
    "trim.player": {"en": "▶  Player && Cut Points", "tr": "▶  Oynatıcı && Kesim Noktaları"},
    "trim.duration": {"en": "Duration: {d}", "tr": "Süre: {d}"},
    "trim.duration_none": {"en": "Duration: —", "tr": "Süre: —"},
    "trim.volume": {"en": "Volume:", "tr": "Ses:"},
    "trim.play": {"en": "▶  Play", "tr": "▶  Oynat"},
    "trim.pause": {"en": "⏸  Pause", "tr": "⏸  Duraklat"},
    "trim.set_start": {"en": "◀  Start Here", "tr": "◀  Buradan Başlat"},
    "trim.set_end": {"en": "End Here  ■", "tr": "Burada Bitir  ■"},
    "trim.set_start_tip": {"en": "Use the current position as the cut start",
                           "tr": "Şu anki konumu kesim başlangıcı yap"},
    "trim.set_end_tip": {"en": "Use the current position as the cut end",
                         "tr": "Şu anki konumu kesim sonu yap"},
    "trim.start": {"en": "Start:", "tr": "Başlangıç:"},
    "trim.end": {"en": "End:", "tr": "Bitiş:"},
    "trim.no_player": {"en": "No player", "tr": "Oynatıcı yok"},
    "trim.no_backend": {"en": "⚠ Multimedia backend not available: {d}",
                        "tr": "⚠ Multimedia altyapısı bulunamadı: {d}"},
    "trim.button": {"en": "✂  Trim & Save", "tr": "✂  Kes & Kaydet"},
    "trim.bad_range": {"en": "The end time must be after the start time.",
                       "tr": "Bitiş zamanı başlangıçtan sonra olmalı."},

    # ── Extract tab ────────────────────────────────────────────────────────
    "extract.banner": {
        "en": "🎬  Pull the audio track straight out of your videos.\n"
              "Native mode copies the audio stream as-is — no re-encoding, no quality loss, maximum speed.",
        "tr": "🎬  Videolardaki ses akışını doğrudan çıkarın.\n"
              "Native mod ses akışını olduğu gibi kopyalar — yeniden kodlama yok, kalite kaybı yok, en yüksek hız."},
    "extract.mode": {"en": "🔧  Extraction Mode", "tr": "🔧  Çıkarma Modu"},
    "extract.native": {"en": "Native / lossless copy — keep the audio stream exactly as it is",
                       "tr": "Native / kayıpsız kopya — ses akışını olduğu gibi kopyala"},
    "extract.reencode": {"en": "Re-encode to:", "tr": "Yeniden kodla:"},
    "extract.button": {"en": "🎬  Extract Audio", "tr": "🎬  Sesi Çıkar"},

    # ── Convert tab ────────────────────────────────────────────────────────
    "convert.button": {"en": "▶  Convert All", "tr": "▶  Hepsini Dönüştür"},

    # ── Actions / status ───────────────────────────────────────────────────
    "action.cancel": {"en": "■  Cancel", "tr": "■  İptal"},
    "action.retry": {"en": "↺  Retry Failed", "tr": "↺  Başarısızları Yeniden Dene"},
    "action.open_folder": {"en": "📂  Open Folder", "tr": "📂  Klasörü Aç"},
    "status.pending": {"en": "Waiting", "tr": "Bekliyor"},
    "status.working": {"en": "Working… {p}%", "tr": "İşleniyor… %{p}"},
    "status.done": {"en": "✔ Done", "tr": "✔ Tamam"},
    "status.failed": {"en": "✖ Failed", "tr": "✖ Başarısız"},
    "status.cancelled": {"en": "Cancelled", "tr": "İptal edildi"},
    "status.processing": {"en": "⏳  Processing {i}/{n}: {name}", "tr": "⏳  İşleniyor {i}/{n}: {name}"},
    "status.summary": {"en": "Finished: {ok} succeeded, {fail} failed.",
                       "tr": "Bitti: {ok} başarılı, {fail} başarısız."},
    "status.summary_cancel": {"en": "Cancelled after {ok} file(s).",
                              "tr": "{ok} dosyadan sonra iptal edildi."},
    "status.saved": {"en": "✔  Saved: {path}", "tr": "✔  Kaydedildi: {path}"},
    "msg.no_files_title": {"en": "No Files", "tr": "Dosya Yok"},
    "msg.no_files": {"en": "Please add at least one file.", "tr": "Lütfen en az bir dosya ekleyin."},
    "msg.no_file": {"en": "Please choose a source file.", "tr": "Lütfen bir kaynak dosya seçin."},
    "msg.error": {"en": "Error", "tr": "Hata"},
    "msg.errors_title": {"en": "Some files failed", "tr": "Bazı dosyalar başarısız oldu"},
    "err.header": {"en": "Resize this window to see the full message. You can select and copy the text.",
                   "tr": "Mesajın tamamını görmek için pencereyi büyütebilirsiniz. Metni seçip kopyalayabilirsiniz."},
    "err.copy": {"en": "📋  Copy", "tr": "📋  Kopyala"},
    "err.close": {"en": "Close", "tr": "Kapat"},

    # ── Metadata ───────────────────────────────────────────────────────────
    "meta.files": {"en": "📂  Files to Tag", "tr": "📂  Etiketlenecek Dosyalar"},
    "meta.editor": {"en": "🏷  Tags", "tr": "🏷  Etiketler"},
    "meta.title": {"en": "Title:", "tr": "Başlık:"},
    "meta.artist": {"en": "Artist:", "tr": "Sanatçı:"},
    "meta.album": {"en": "Album:", "tr": "Albüm:"},
    "meta.album_artist": {"en": "Album artist:", "tr": "Albüm sanatçısı:"},
    "meta.date": {"en": "Year / Date:", "tr": "Yıl / Tarih:"},
    "meta.genre": {"en": "Genre:", "tr": "Tür:"},
    "meta.track": {"en": "Track #:", "tr": "Parça no:"},
    "meta.disc": {"en": "Disc #:", "tr": "Disk no:"},
    "meta.composer": {"en": "Composer:", "tr": "Besteci:"},
    "meta.comment": {"en": "Comment:", "tr": "Yorum:"},
    "meta.col_title": {"en": "Title", "tr": "Başlık"},
    "meta.col_artist": {"en": "Artist", "tr": "Sanatçı"},
    "meta.col_album": {"en": "Album", "tr": "Albüm"},
    "meta.multiple": {"en": "‹multiple values — leave empty to keep›",
                      "tr": "‹farklı değerler — boş bırakırsanız korunur›"},
    "meta.select_hint": {"en": "Select one or more files on the left to edit their tags.",
                         "tr": "Etiketlerini düzenlemek için soldan bir veya daha fazla dosya seçin."},
    "meta.editing": {"en": "Editing {n} file(s). Only fields you change are written.",
                     "tr": "{n} dosya düzenleniyor. Yalnızca değiştirdiğiniz alanlar yazılır."},
    "meta.cover": {"en": "Cover art", "tr": "Kapak görseli"},
    "meta.no_cover": {"en": "No cover", "tr": "Kapak yok"},
    "meta.cover_multi": {"en": "Several files", "tr": "Birden çok dosya"},
    "meta.cover_new": {"en": "New cover\n(will be saved)", "tr": "Yeni kapak\n(kaydedilecek)"},
    "meta.cover_removed": {"en": "Cover will be\nremoved", "tr": "Kapak\nkaldırılacak"},
    "meta.cover_choose": {"en": "Choose Image…", "tr": "Görsel Seç…"},
    "meta.cover_remove": {"en": "Remove Cover", "tr": "Kapağı Kaldır"},
    "meta.cover_export": {"en": "Export Cover…", "tr": "Kapağı Dışa Aktar…"},
    "meta.cover_unsupported": {"en": "Cover art is supported for MP3, FLAC and M4A/MP4 files only.",
                               "tr": "Kapak görseli yalnızca MP3, FLAC ve M4A/MP4 dosyalarında desteklenir."},
    "meta.from_filename": {"en": "Fill from File Name", "tr": "Dosya Adından Doldur"},
    "meta.from_filename_tip": {"en": "Reads 'Artist - Title' (and '01 - …' track numbers) from each file name",
                               "tr": "Her dosya adından 'Sanatçı - Başlık' (ve '01 - …' parça numarası) okur"},
    "meta.auto_track": {"en": "Number Tracks", "tr": "Parçaları Numarala"},
    "meta.auto_track_tip": {"en": "Sets track numbers 1, 2, 3… in list order",
                            "tr": "Liste sırasına göre 1, 2, 3… parça numarası verir"},
    "meta.revert": {"en": "Revert", "tr": "Geri Al"},
    "meta.save": {"en": "💾  Save Tags", "tr": "💾  Etiketleri Kaydet"},
    "meta.apply": {"en": "Apply", "tr": "Uygula"},
    "meta.cancel": {"en": "Cancel", "tr": "Vazgeç"},
    "meta.dialog_title": {"en": "Tags for converted files", "tr": "Dönüştürülecek dosyaların etiketleri"},
    "meta.dialog_hint": {"en": "These tags are written to the output files. The source files are not changed.",
                         "tr": "Bu etiketler çıktı dosyalarına yazılır. Kaynak dosyalar değişmez."},
    "meta.unsupported": {"en": "Tag editing is not supported for this format (skipped).",
                         "tr": "Bu formatta etiket düzenleme desteklenmiyor (atlandı)."},
    "meta.saved": {"en": "✔  Tags saved to {n} file(s).", "tr": "✔  Etiketler {n} dosyaya kaydedildi."},
    "meta.nothing": {"en": "Nothing changed.", "tr": "Değişiklik yok."},
    "meta.only_tag_formats": {
        "en": "Only formats that can store tags are listed (MP3, FLAC, M4A, OGG, OPUS, WMA, WAV, AIFF, MKA).",
        "tr": "Yalnızca etiket saklayabilen formatlar listelenir (MP3, FLAC, M4A, OGG, OPUS, WMA, WAV, AIFF, MKA)."},
}


def detect_system_language():
    try:
        lang = (locale.getlocale()[0] or "").lower()
    except Exception:
        lang = ""
    if not lang:
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if (lcid & 0x3FF) == 0x1F:   # LANG_TURKISH
                return "tr"
        except Exception:
            pass
    return "tr" if lang.startswith("tr") or "turkish" in lang else "en"


def set_language(code):
    global _current
    _current = code if code in LANGUAGES else "en"


def current_language():
    return _current


def tr(key, **kwargs):
    entry = STRINGS.get(key)
    if entry is None:
        text = key
    else:
        text = entry.get(_current) or entry.get("en") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text
