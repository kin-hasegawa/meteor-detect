# meteor-detect

ATOMCamのストリーミング及びデータからの流星を自動検出<br>
Automatic meteor detection from movie files(MP4) and streaming devices(RTSP)

無保証、無サポートです。

元々、人に公開する目的で作ったのではなく、ソースコードのコメントも自分のためのメモ程度で極めて不親切。
予告なしに仕様変更、機能追加(削除)を行います。

## 概要

安価なATOM Cam2(防水型の夜間監視カメラ)というオモチャを手に入れて、ベランダに設置して2022年1月4日のしぶんぎ座流星群を撮影した。
しかし、後から目視で動画から流星を検出するのが大変なので、なんとか自動化できないか検討した。動画を見て数える何倍もの時間をかけて自動流星検知を作成した。でも、楽しい。以下のことを目標に開発。

* ATOM Cam2 からのストリーミングデータ(RTSP配信)をリアルタイムで解析し、流星を検知すること。
* ATOM Cam2 による撮影済みの動画データ(MP4)を解析して、流星を検知すること。
* YouTubeのライブストリーミングデータを解析して、流星を検知すること。(実験中)

実際に使ってみた結果、流星検出能力は人間と同程度。人間も見落とすし、自動検知も見落とす。<br>
現状、流星と飛行機の区別ができていない場合があるため、最後は該当動画を目視で確認する必要あり。

## 動作環境

* ネットワークカメラ
  * ATOM Cam2、及び、ATOM Cam Swingで動作確認。

<p align="center">
  <img src="images/ATOM_Cam2.jpeg" alt="ATOM Cam2" width="80%">
</p>

* PC環境
  * macOS 11, 12 (Intel Mac, M1 Mac) , Ubuntu 20.04LTS, Ubuntu 22.04LTS で動作確認。
  * Windows10/11で動作したという報告もある。
  * Python 3.8以上で動作確認<br>
  (2022/08/13現在、Python3.10/Ubuntu 22.05LTS で動作確認)

* 必要なソフトウエア
  * PC側
    * Python 3.X
    * OpenCV
    * NumPy
    * ffmpeg
  * ATOM Cam側 (ATOMCam 2の場合は不要)
    * atomcam_tools.zip

ATOMCam2のファームウェアバージョン4.58.0.91 以降から正式に RTSP をサポートしたので　atomcam_tools のインストールがなくてもリアルタイム検出が可能になった。ただし、ATOMCam Swingの場合はこれがないとRTSP配信ができないので必要となる。


### atomcam-toolsのインストール (オプショナル)

最新のファームウェア(4.58.0.91以降)の場合、以下のatomcam-tools のインストールは不要となった。このセクションを飛ばしても良い。
(ただし、ATOMCam Swingの方はRTSP未サポートのためまだ atomcam-tools が必要。)


atomcam-tools は、[hanyeylab](https://honeylab.hatenablog.jp/about) さんが作成された ATOM Cam RTSPサーバー、FTP、TELNETサーバー等の機能を追加するツールである。カメラ上でLinuxのカーネルを稼働させて、それらの機能を提供している。
SDカードにダウンロードしたファイルをコピーしてカメラの再起動を行うだけでインストールができる。

以下のサイトから atomcam_tools.zip をダウンロードしてATOM Cam2にインストールする。

- [ATOMCam2の機能拡張用ツールを公開しました](https://honeylab.hatenablog.jp/entry/2021/09/24/002107)
- [ダウンロード](https://github.com/bakueikozo/atomcam_tools/releases/download/v1.0rc/atomcam_tools.zip) はここから。

インストールして、ATOM Camを再起動すると使えるようになる。
telnetでカメラにrootアカウントでログインすることができる。デフォルトのパスワードはカメラの名前(ATOM Cam2の場合は'atomcam2')。
ただし、メーカーサポート外の使い方になるので、今後 ATOM Cam側のファームウェアのアップデートによってはこのツールが使えなくなる可能性もあるので自己責任でどうぞ。

haneylabさんのオリジナルに対して改良版で、SSHなども追加されたものもあるが、ここではオリジナル版のみに対応している。
動作については未確認であるが、改良版ではtelnetの代わりにSSHを使っているので、内部でATOM Camの時刻を取得するところで動作しない。

- [atomcam_tools改良版](https://github.com/mnakada/atomcam_tools)


カメラのIPアドレスは、ATOM Camのアプリのデバイス情報で確認することができる。下記の例は私のローカルネットワーク内のカメラのIPで接続した例。

```
% telnet 192.168.2.110
Trying 192.168.2.110...
Connected to 192.168.2.110.
Escape character is '^]'.

Ingenic login: root
Password: 
[root@Ingenic:~]# ls
aback     dev       lib       mnt       root      sys       tmp
bin       etc       linuxrc   opt       run       system    usr
configs   kback     media     proc      sbin      thirdlib  var
```

カメラ上のデータは、以下のところに保存されている。

```
[root@Ingenic:~]# ls media/mmc/record/
20220114  20220116  20220118  20220120  20220122  20220124
20220115  20220117  20220119  20220121  20220123  20220125
```

#### ATOM Cam2の内蔵時計

ATOM Cam2の内蔵時計は起動時にWi-Fiルータ経由で設定されるものの、その後はネットワークを通してNTPと同期していないために、時間と共にずれていく。
みんなどうやって合わせてるのだろうか？ アプリにも時刻設定メニューが見当たらない。

とりあえず、telnet で入れるので、[JST Clockサイト](https://www.nict.go.jp/JST/JST5.html)を見ながら、dateコマンドで強制的に時刻を設定する。
時刻はUTCなので注意。

```
# date -s "2022-01-23 13:36"
```

しかし、最も簡単な方法は再起動することかもしれない。

```
# reboot
```

ただし、内蔵時計を操作するには atomcam_tools が必要となる。atomcam_toolsがない場合は電源の再投入以外に方法はない。

#### ATOM Cam2の動体検知

デフォルトのATOM Cam2では動体検知が動いているので、これをOFFにする。動体検知の枠線が自動検出の邪魔になるため。
また、同様に左下のロゴマークも邪魔なのでOFFにする。

### OpenCVのインストール

OpenCVはC/C++で書かれた強力な汎用画像処理ライブラリで、Pythonから利用することができる。

#### macOS/Ubuntuの場合

Python3環境は仮想環境を使うとシステム標準環境のPython(macOSの場合は2.7が標準となっている)と分けて使える。

Python仮想環境の作り方については「Python 仮想環境 venv」などをキーワードにしてGoogle先生にお尋ねください。
以下、Python3.Xの仮想環境下であることを想定しています。

```
% pip install ffmpeg
% pip install opencv-python
% pip install imutils
```

numpyは opencv-pythonのインストール時に行われる。

#### YouTubeライブストリーミング対応

YouTube動画のURLを扱うために下記パッケージが必要になる。

```
% pip install yt-dlp
% pip install pafy
```

当初 `youytube_dl` を使っていたが、YoutTube側の仕様変更に対応するメンテナンスされていないので、`yt-dlp` を使うようにしました。
また、以前使っていた `apafy` は最新のPythonのバージョンではインストールできなくなったので、`pafy` に戻しました。

`pafy`もその後のYouTubeの仕様変更に対応していないために若干の修正が必要とな離ます。

ただし、YouTube動画を扱わない場合は修正は不要。

修正対象のファイルのpathです(Python 3.10の場合)。

```
<インストールディレクトリ>/lib/python3.10/site-packages/pafy/backend_youtube_dl.py
```

インストール先はOSやPythonの仮想環境(venv etc.)によって異なるので確認してください。
修正箇所は下記の3箇所です(pafy==0.5.5の場合)。
(この修正は自己責任でお願いします)

- yt_dlpのimport
```
#import youtube_dl  <-- youtube_dl の代わりに  yt_dlp を import する。
import yt_dlp as youtube_dl
```
  
- class YtdlPafy 内の修正
```
class YtdlPafy(BasePafy): の中の

    def _fetch_basic(self):の中


        #self._length = self._ydl_info['duration']     <-- コメントアウト

        #self._likes = self._ydl_info['like_count']         <-- この2行をその下の2行に置き換え。
        #self._dislikes = self._ydl_info['dislike_count']
        self._likes = self._ydl_info.get('like_count',0)
        self._dislikes = self._ydl_info.get('dislike_count',0)
```

- class YtdlStream 内の修正

```
class YtdlStream(BaseStream): の中の
    def __init__(self, info, parent): の中、

        #self._rawbitrate = info.get('abr', 0) * 1024  <-- この行を以下の2行に置き換え。 
        abr = info.get('abr', 0) if info.get('abr',0) is not None else 0
        self._rawbitrate = abr * 1024

```

## 流星検出方法

1. 流星が流れる時間程度(1~2秒)で差分画像リストを作成する(流星のみを残す)。
1. 差分画像のリストを比較明合成し移動天体を抽出する。
1. 移動天体の中から流星と思われる直線状のパターンを検出する。
1. 検出メッセージ(時刻)を出力し、その比較明合成画像、及び動画を保存する。

流星を検出する際に、画面右下のタイムスタンプでノイズが出ることがあったのでタイムスタンプ部分にマスクをかけている。
その他、地上の建物に光が当たったり、電線が揺れた場合でもノイズを疲労ことがあるので環境に合わせてマスクをかけた方が誤認識は減るはずである。


```
def brightest(img_list):
    """比較明合成処理
    Args:
      img_list: 画像データのリスト

    Returns:
      比較明合成された画像
    """
    output = img_list[0]

    for img in img_list[1:]:
        output = np.where(output > img, output, img)

    return output


def diff(img_list, mask):
    """画像リストから差分画像のリストを作成する。

    Args:
      img_list: 画像データのリスト
      mask: マスク画像(2値画像)

    Returns:
      差分画像のリスト
    """
    diff_list = []
    for img1, img2 in zip(img_list[:-2], img_list[1:]):
        img1 = cv2.bitwise_or(img1, mask)
        img2 = cv2.bitwise_or(img2, mask)
        diff_list.append(cv2.subtract(img1, img2))

    return diff_list
```

マスク画像はATOM Camのタイムスタンプ更新でノイズが入るのでマスク画像を用意して消すようにした。
ATOM Cam以外のカメラを使う場合は、別途マスク画像を用意する必要がある。

画像からの流星の検出方法は下記のサイトで紹介されている方法を参考にした(R. Sparrius, 2020)。

[D64.NL – METEOR DETECTING PROJECT](https://www.meteornews.net/2020/05/05/d64-nl-meteor-detecting-project/)

まだ流星と飛行機、人工衛星の区別がまだ十分にできていない。また、東京の空ではS/Nが悪いため暗い流星は検出できない。

`minLineLength`の値が検出する線状パターンの長さ。これを長くすると遅い飛行機、人工衛星を除外できるが、経路の短い流星を見落としてしまう。


```
def detect(img, min_length, sigma=0):
    """画像上の線状のパターンを流星として検出する。
    Args:
      img: 検出対象となる画像
      min_length: HoughLinesPで検出する最短長(ピクセル)
      igma: sigma parameter of GaussinaBlur()
    Returns:
      検出結果
    """
    blur_size = (5, 5)
    blur = cv2.GaussianBlur(img, blur_size, sigma)
    canny = cv2.Canny(blur, 100, 200, 3)

    # The Hough-transform algo:
    return cv2.HoughLinesP(canny, 1, np.pi/180, 25, minLineLength=min_length, maxLineGap=5)
```

## 使い方

### 事前の準備

ソースコードの下記の行を自分のATOM CamのIPに合わせて修正してください。

```
# 自分の環境のATOM CamのIPに修正してください。
ATOM_CAM_IP = os.environ.get("ATOM_CAM_IP", "192.168.2.110")
```

ATOM CamのIPアドレスは固定IPアドレスではなく、Wi-FiルータのDHCP(あるいはルータの設定によって固定も可)によって決まるので、
ルーターの設定によってはIPアドレスが変更される場合があるので注意。ルータ側でATOM CamのMACアドレスを登録して同じIPアドレスが割り当てられるようにしておくとよい。

ATOM CamのIPアドレスはコマンド起動時に引数で指定することもできます。また環境変数(ATOM_CAM_IP)に設定しておくと、それがデフォルトになる。

```
export ATOM_CAM_IP=192.168.2.110
```

また、atomcam_toolsのtelnetインターフェースを通してATOM Camの内蔵時計の値を表示し、ホストPC側との差を表示するには(`-c` または `--clock` オプションで指定)、以下の部分を修正してください。

```
# atomcam_toolsでのデフォルトのユーザアカウントなので、自分の環境に合わせて変更してください。
ATOM_CAM_USER = "root"
ATOM_CAM_PASS = "atomcam2"
```

以下は、コマンドオプションの一覧。

```
usage: atomcam.py [-u URL] [-n] [-d DATE] [-h HOUR] [-m MINUTE] [-i INPUT] [-e EXPOSURE] [-o OUTPUT] [-t TO]
                  [--mask MASK] [--min_length MIN_LENGTH] [--sigma SIGMA] [--opencl] [-s] [--thread] [--help]
                  [--atomcam_tools] [-c]

options:
  -u URL, --url URL     RTSPのURL、または動画(MP4)ファイル
  -n, --no_window       画面非表示
  -d DATE, --date DATE  Date in 'yyyymmdd' format (JST)
  -h HOUR, --hour HOUR  Hour in 'hh' format (JST)
  -m MINUTE, --minute MINUTE
                        minute in mm (optional)
  -i INPUT, --input INPUT
                        検出対象のTOPディレクトリ名
  -e EXPOSURE, --exposure EXPOSURE
                        露出時間(second)
  -o OUTPUT, --output OUTPUT
                        検出画像の出力先ディレクトリ名
  -t TO, --to TO        終了時刻(JST) "hhmm" 形式(ex. 0600)
  --mask MASK           mask image
  --min_length MIN_LENGTH
                        minLineLength of HoghLinesP
  --sigma SIGMA         sigma parameter of GaussianBlur()
  --opencl              Use OpenCL (default: False)
  -s, --suppress-warning
                        suppress warning messages
  --thread              スレッド版(default)
  --help                show this help message and exit
  --atomcam_tools       atomcam_toolsを使う場合に指定する。
  -c, --clock           カメラの時刻チェック(atomcam_tools必要)
```

`--thread`オプションは現在デフォルトとして設定しているので不要になるが、前のバージョンとの関係で形だけ残してある。
いずれ削除する予定。

### リアルタイムに流星検出を行う

以下、`atomcam.py`コマンドがあるディレクトリ下での実行を想定している。必要であればPATHの通った場所に置く。

デフォルト状態での実行例

```
% ./atomcam.py
```

デフォルトのRTSPサーバーからストリーミングサーバーからデータを読み込み、流星検出を試みる。ウインドウが表示され、比較明合成画像が1秒毎に更新される。流星が検出されると日時とメッセージがコンソールに出力される。

以下はコマンドの出力例。この例で見つかっているのは飛行機。

```
# end_time =  2022-01-15 06:00:00
# 2022/01/15 00:00:00 started.
2022/01/15 00:19:31 A possible meteor was detected.
2022/01/15 00:19:34 A possible meteor was detected.
2022/01/15 00:19:37 A possible meteor was detected.
2022/01/15 00:19:39 A possible meteor was detected.
2022/01/15 00:19:42 A possible meteor was detected.
...
```

実行すると、検出時の比較明合成画像(jpeg)、動画(mp4)、及び1時間毎にスカイモニター画像(jpeg)が出力される。

- `yyyymmddhhmmss.jpg` (検出時の比較明合成画像)
- `movie-yyyymmddhhmmss.mp4` (検出時の動画)
- `sky-yyyymmddhhmmss.jpg` (スカイモニター画像)

これらのファイルはデフォルトではコマンドを起動したディレクトリ下に作成される。出力先ディレクトリ名を以下のオプションで指定することができる。日付などをディレクトリ名を作成しておくと後で整理しやすいだろう。

```
-o 出力先ディレクトリ名

または、

--output 出力先ディレクトリ名
```

以下は自宅環境のログ出力の例。Wi-Fi環境が悪く、パケットロスにより動画をデコードに失敗した場合に出るエラー(h264エラー)。
接続が切れた場合は再接続を試みて続行するようにしている。


```
[h264 @ 0x7fa9440c8700] error while decoding MB 51 51, bytestream -5
[h264 @ 0x7fa9440c8700] error while decoding MB 114 65, bytestream -43
[h264 @ 0x7fa946c262c0] error while decoding MB 116 17, bytestream -5
2022/01/25 00:34:35 A possible meteor was detected.
2022/01/25 00:34:42 A possible meteor was detected.
[h264 @ 0x7fa947e41080] error while decoding MB 40 57, bytestream -5
[h264 @ 0x7fa947e282c0] error while decoding MB 102 45, bytestream -5
2022/01/25 01:09:15 A possible meteor was detected.
2022/01/25 01:15:31 A possible meteor was detected.
2022/01/25 01:29:58 A possible meteor was detected.
2022/01/25 01:32:03 A possible meteor was detected.
[h264 @ 0x7fa947e41080] error while decoding MB 82 
```
回線状態が良ければ上記のエラーはでない。

エラー出力が鬱陶しい場合は、起動時のオプションで、

```
-s
```

または、

```
--suppress-warning
```

を追加すると表示されなくなる。

<p align="center">
  <img src="images/20220104050908.jpg" alt="QUA Meteor" width="80%">
  <br>
  比較明合成で検出された流星画像の例。
</p>

RTSPのURLを指定して起動する例。

```
% ./atomcam.py -u rtsp://192.168.2.110:8554/unicast
```


teeコマンドを合わせて使うと、画面にログを表示すると共に、ファイルに書き出すことができる。

```
% ./atomcam.py | tee -a 20220104.log
```

teeコマンドの`-a`オプションは追記で、オプションなしの場合は上書きされる。

#### ATOM Cam内クロックの時刻表示

`-c` または `--clock` オプション指定で起動時にATOM Cam側のクロックを表示させた場合の例(ATOM Camの user/pass を設定する必要があるので注意)。

(atomcam_toolsの新しいバージョンではJST表示なっているので、下記の昨日は9時間ずれる可能性あり。作者は未確認)

```
% ./atomcam.py -c
# end_time =  2022-01-31 06:00:00
# ATOM Cam = 2022-01-30 02:51:58+00:00
# HOST PC  = 2022-01-30 02:51:56.475220+00:00
# ATOM Cam - Host PC = 0:00:01.524780
# 2022/01/30 11:51:56 start
# threading version started.
```

この例では1秒ほどATOM Camの方が時計が進んでいることが分かる。ATOM Cam側から1秒以下の時刻は取れないが、他の観測と出現時刻を比較する時には参考になる。

### 動画ファイル(ATOM Cam形式のディレクトリ)から流星検出を行う

#### ATOM Camのデータ

リアルタイムではなく、後日撮影データから流星を検知する場合は、ATOM Camからのデータをダウンロード、あるいはSDカードからコピーする必要がある。

あるいはNAS出力を設定していればダウンロードの必要はない。

ディレクトリ構造は日付毎に以下のようになっている。

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

#### データのダウンロード

ATOM Camからのデータのダウンロードは、好みのFTPクライアントで行う。FTPのアカウントもtelnetログインの場合と同じで、デフォルトでは、`root/カメラ名`である。

以下はwgetコマンドを使ってダウンロードする例。

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

#### FTPスクリプト(おまけ)

指定時刻範囲のデータをまとめてダウンロードするためのスクリプト(atom_ftp.sh)を用意した。
(接続情報は環境に合わせて修正する必要あり。)

```
# 下記の接続情報を自分の環境に合わせて修正してください。
ATOMCAM_IP='192.168.2.110'
ATOMCAM_USER=root
ATOMCAM_PASS=atomcam2
```

以下のコマンドでダウンロードが可能。

```
% ./atom_ftp.sh 20220104 1 2
```

とやることで、カレントディレクトリ以下に指定時刻(1〜2時)のデータをダウンロードできる。

```
20220104/01/*.mp4
20220104/02/*.mp4
```

#### 実行例

date=20220109 の日付の 01時台の1時間分のデータから流星検出を行う場合の例。

```
% ./atomcam.py -d 20220109 -h 01
```

1時間分の流星検出に約8分ほどかかった(M1 MacBookAirの場合)。古い Intel Core i-5のPCで24分程度。

ATOM Cam形式のディレクトリ構造の場合、ファイルのpathとファイル名から流星検出時刻を推定して出力する。

<p align="center">
  <img src="images/しぶんぎ.gif" alt="QUA Meteor" width="80%">
  <br>
  検出された流星動画のオリジナル。
</p>


### 動画ファイル(MP4)から流星検出を行う

```
% ./atomcam.py -u 20220109/01/05.mp4
```

単純にMP4ファイルを指定した場合は、流星検出時刻は推定できないので、現在時刻を表示するみ。
(開始時刻からの秒数も分かるといいかも)

### YouTubeのライブストリーミングから流星検出を行う。

まだ動作が不安定なことがあり、ネットワーク回線の影響で接続が切れた場合の再接続に失敗する場合がある。
また、URLが時々変更されることがあるので、その場合にプログラム側で対応する必要あるので、使えなくなることもある。

`--url`オプションでYouTube動画のURLを指定する。(URLにはダブルクォートで括る必要あり)

検出時刻はスクリプトを起動しているPCの時刻になる。マウナケアの動画からもJSTで表示するので、画面のタイムスタンプには時差が生じているので注意。加えて撮影カメラからYouTubeを通して配信までに10秒程度の遅延があるので記録された出現時刻にはその程度の誤差がある。

#### マウナケア

```
% ./atomcam.py --url "https://www.youtube.com/watch?v=_8rp1p_tWlc"
```

<p align="center">
  <img src="images/20220312000929.jpg" alt="QUA Meteor" width="80%">
  <br>
  検出された流星の比較明合成画像。
</p>

国立天文台ハワイ観測所と朝日新聞科学部提供

#### 東大木曽観測所

```
% ./atomcam.py --url "https://www.youtube.com/watch?v=mrusJKLhxAw"
```

<p align="center">
  <img src="images/20220311013532.jpg" alt="QUA Meteor" width="80%">
  <br>
  検出された流星の比較明合成画像。
</p>

東京大学木曽観測所と朝日新聞科学部提供

#### 福島星空ライブ

```
% ./atomcam.py --url "https://www.youtube.com/watch?v=SDRS6JQulmI"
```

朝日新聞科学部提供

## 暫定結果

2022年1月4日のしぶんぎ流星群のデータでの検証。

### 杉並

2022年1月4日に、東京都杉並区で南の空に向けた動画から検出した流星。(一部飛行機が含まれている)

<p align="center">
  <img src="images/meteor.gif" alt="QUA Meteor" width="80%">
  <br>
  検出された流星の比較明合成画像を繋げた動画。
</p>


### 高崎

```
鈴木文二さんの01/04の5時台のデータ調査。

          目視   自動検出
-----------------------
05:01:04  x     o
05:02:24  x     o
05:02:24  x     o
05:03:14  o     o
05:07:20  x     o
05:07:36  o     x  真ん中下の方短経路
05:08:46  x     o
05:09:07  o     x  <-- 分からない。
05:09:08  o     o
05:09:40  x     o
05:11:49  o     x  左側短経路
05:13:36  o     x  淡い
05:16:18  x     o
05:20:21  o     o
05:21:40  x     o
05:24:05  o     o
05:24:51  o     o
05:25:16  o     o
05:26:50  o     o
05:29:27  x     o
05:29:34  o     o
05:29:55  o     o
05:30:24  o     o
05:32:16  x     o
05:33:56  x     o
05:39:09  o     o
05:42:05  o     x  右下の方の短経路
05:43:00  o     o
05:46:50  o     x  淡い
05:50:58  o     o
05:53:46  o     x  真ん中下
05:53:54  o     x  真ん中ぐらい、淡い
05:55:04  x     o
05:56:47  o     o

  全流星  34個
  目視    23個
  自動    26個
  重複    14個
  目視のみ 8
  自動のみ 12個
```

