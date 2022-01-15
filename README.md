# meteor-detect

ATOMCamのストリーミング及びデータからの流星を自動検出<br>
Detecton of  meteors in movie files or streaming devices

無保証、無サポートです。

## 準備

ATOM Cam 2 及び、Python 3.8以上で動作確認(macOS, Ubuntu)。

* atomcam_tools.zip
* OpenCV

### atomcam-toolsのインストール

atomcam-tools は、ATOM Cam RTSPサーバー、FTP、TELNETサーバー等の機能を追加するツールです。
SDカードにダウンロードしたファイルをコピーしてカメラの再起動を行うだけでインストールができます。

以下のサイトから atomcam_tools.zip をダウンロードしてATOM Cam2にインストールします。

- [ATOMCam2の機能拡張用ツールを公開しました](https://honeylab.hatenablog.jp/entry/2021/09/24/002107)
- [ダウンロード](https://github.com/bakueikozo/atomcam_tools/releases/download/v1.0rc/atomcam_tools.zip)

インストール直後の

### OpenCVのインストール

#### macOS/Ubuntuの場合

```
% pip install ffmpeg
% pip install opencv-python
% pip install imutils
```

## データ

ATOM Camからのデータは、SDカードあるいは atomcam_tools によるFTPダウンロードします。

ディレクトリ構造は日付毎に以下のようになっています。

```
% tree 20220114
20220114
└── 23
    ├── 00.mp4
    ├── 01.mp4
    ├── 02.mp4
    ├── 03.mp4
    ├── 04.mp4

以下省略

```

### データのダウンロード

wgetコマンドを使うとまとめてダウンロードすることができます。

日付を指定して一括ダウンロードする例:

```
% wget -r -nv -nH --cut-dirs=3 ftp://root:atomcam2@192.168.2.111/media/mmc/record/20220104
```

日付時刻を指定して1時間分のデータをダウンロードする例:

```
% wget -r -nv -nH --cut-dirs=3 ftp://root:atomcam2@192.168.2.111/media/mmc/record/20220104/01
```

wgetコマンドのインストール方法

#### macOS

```
% brew install wget
```

#### Ubuntu

```
$ sudo apt install wget
```

#### FTPスクリプト

指定範囲のデータをまとめてダウンロードするためのスクリプト(atom_ftp.sh)を用意しました。

```
% ./atom_ftp.sh 20220104 1 2
```

とやることで、カレントディレクトリ以下に指定時刻(1〜2時)のデータをダウンロードできます。

```
20220104/01/*.mp4
20220104/02/*.mp4
```

## 使い方

ソースコードの下記の行を自分のATOM CamのIPに合わせて修正してください。

```
# 自分の環境のATOM CamのIPアドレスに変更してください。
ATOM_CAM_RTSP = 'rtsp://192.168.2.111:8554/unicast'
```

以下は、コマンドオプションの一覧。

```
% ./atomcam.py -h
usage: atomcam.py [-h] [-u URL] [-n] [-d DATE] [--hour HOUR] [-m MINUTE] [-i INPUT] [-e EXPOSURE] [-o OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     RTSPのURL、または動画(MP4)ファイル
  -n, --no_window       画面非表示
  -d DATE, --date DATE  Date in 'yyyymmdd' format (JST)
  --hour HOUR           Hour in 'hh' format (JST)
  -m MINUTE, --minute MINUTE
                        minute in mm (optional)
  -i INPUT, --input INPUT
                        検出対象のTOPディレクトリ名
  -e EXPOSURE, --exposure EXPOSURE
                        露出時間(second)
  -o OUTPUT, --output OUTPUT
                        検出画像の出力先ディレクトリ名
```

### リアルタイムに流星検出を行う

実行例
```
% ./atomcam.py -u 
```

### 動画ファイル(MP4)から流星検出を行う

```
% ./atomcam.py -u 20220109/01/05.mp4
```

