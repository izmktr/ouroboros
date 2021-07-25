# 2021年7月以降クランバトル用ユカリさん
project code:ouroboros

プリンセスコネクト:Re Diveのクランバトル用discord botです  

最低限これだけ覚えておくべき、というビギナー向けの解説を[こちら](document/biggner.md)においています

# コマンド
凸報告のチャンネルで入力します  
凸系コマンド以外はbotにメンションすることでどこのチャンネルでも使うことが出来ます  
例) @ユカリさん dice

## 凸系コマンド
ボスに凸宣言をするコマンドです

### 凸/a
凸 [ボス番号]  

ボスを攻撃するときに使います  

例)  
凸1  
1番めのボスに凸宣言します

コマンドを入れるとユカリさんがスタンプを付けます  
凸後の行動に応じて対応したスタンプを押します

チェック：ボスを倒してない
数字：ボスを倒した　残り時間の十の位(27秒なら2)
バツ：凸をキャンセル  

間違えた場合、自分の押したスタンプをもう一度押すと  
ユカリさんが再度スタンプを付け直します  
そこで、正しいスタンプを押します

### 持/c
持 [ボス番号][凸回数]  

持ち越しを使って凸宣言します

押すスタンプは同じです  
持ち越し時間を持つことはないので、数字は0のみとなっています

### cancel
凸/持のコマンドを使って凸宣言をした場合、取り消します  
凸コマンドがどこにいったかわからなくなったらこれを使います

### setattack
setattack [アタック記号]

攻撃状態を設定します  

例)setattack 4xo  
1凸目：40秒持ち越し  
2凸目：凸完了  
3凸目：未凸  
に設定します

## ボス調整
ボスの情報を変更するコマンドです

### defeat
defeat [ボス番号]

ボスを討伐済みにします

### undefeat
undefeat [ボス番号]

ボスを未討伐に戻します  

### setboss
setboss [1boss周回数] [2boss周回数] [3boss周回数] [4boss周回数] [5boss周回数]  

ボスの周回数を設定します

## 予約系コマンド

### 予約/reserve
予約 [ボス番号] [コメント]

ボス番号は以下のような入力があります

予約 2  
次周の2ボスを予約します

予約 -2  
この周の2ボスを予約します

予約 10-2  
10周目の2ボスを予約します

予約 +2  
次の次の周の2ボスを予約します

予約のコメント欄に3桁以上の数字を入れるとダメージとして扱い、  
状況報告欄に取りまとめて表示されます

### 予約取り消し/予約取消/unreserve
予約取り消し [ボス番号/all]

予約を取り消します  
「予約取り消し all」と入力すると自分のすべての予約を取り消します

### 配置/place
配置 [ボス番号] [名前] ([名前])  

他のメンバーを予約状態にします
メンバーの名前は複数入力できます

### 配置取り消し/配置取消/unplace
配置取り消し [ボス番号/all] [名前/all] ([名前])  

他のメンバーの予約を取り消します


## ダメコン系

### damagechannel
damagechannel [ボス番号/all]

例)@ユカリさん damagechannel 1
現在入力しているチャンネルをダメコン用チャンネルに指定します  
allと入力すると、そのチャンネルを全ボスのダメコン用チャンネルとします  
以後、凸状態(※)のプレイヤーが以下の発言をするとダメコンとして計算します

※凸状態　凸宣言チャンネルで凸/持を入力し、スタンプをまだ押していない状態

### [数字] [コメント(省略可)]
数字を打ち込むとダメージとして拾います

### [数字+s/秒] [数字] [コメント(省略可)]
3秒 1500 などの入力でもダメージとして拾います

### x[数字(省略可)] [コメント(省略可)]
冒頭にxをつけると無効希望の意思になります  
x のみの発言でもOKです

### @[数字]
@をつけて数字を発言すると、残りHPの設定になります  
この発言のみ、プレイヤーが凸状態でなくても反応します  

### remain [ボス番号] [残りHP]
ボスの残りHPを指定します  
基本的に@[数字]で問題有りませんが、うまく入力できないときに使用します


## 情報系

### サイコロ/dice
100面体サイコロを振ります

### history
history [名前]

名前を入れた人の凸履歴を見ます  
名前を省略すると自分の凸履歴を見ます

### active
1時間以内に書き込みを行ったメンバーを表示します  

### score
score [スコア(万)]

クランスコアから現在の周回数を計算して表示します

## メンバー管理系

### setmemberrole
setmemberrole [ロール名]

ロール名のロールを持つメンバー全員を登録メンバーにします  
全員を登録メンバーにするには @everyone を指定します

### memberdelete
memberdelete [名前]

登録メンバーから指定したメンバーを削除します

### memberinitialize
すべての登録メンバーを削除します

### namedelimiter
namedelimiter [デリミタ]

デリミタ以降の文字を消して名前登録します
「namedelimiter @」と設定すると、@以降を無視します  
「いずみ@45ボス」という名前のメンバーを「いずみ」として扱います

## リセット系処理

### reset
自分の凸数を0に戻します

### dailyreset
メンバー全員の凸数を0に戻します  
朝5時に自動的に実行される処理と同様です

### monthlyreset
全ボスの周回数を1に戻し、メンバー全員の凸数を0に戻します  
クランバトル開始時に自動的に実行される処理と同様です  

## 管理者コマンド

管理者コマンドは加入しているクラン全体に影響のある変更です  
管理者コマンドを使うには、clandata/内にある、jsonを直接編集して  
admin=falseの部分をadmin=trueに変更する必要があります

### settingreload
setting.jsonを読み込み直します

### term
term [開始日付],[終了日付]

例)term 10/26,10/30  
クランバトルの期間を設定します

### bossname
bossname [ボス1名前],[ボス2名前],[ボス3名前],[ボス4名前],[ボス5名前]

例)bossname ゴブリングレート,ワイルドグリフォン,バジリスク,ムーバ,オルレオン  
ボスの名前を設定します  

### clanreport
全クランの状況報告をダウンロードします

## 状況報告

ユカリさんは状況報告に現在の状況を表示します

### プレイヤー名
プレイヤー名の後ろには[x3o]という風なステータスが付きます

* o 未凸
* 数字 持ち越し時間
* x 凸完了

[x3o] と表示されている場合、
* 1凸目 凸完了
* 2凸目 30秒台の持ち越し
* 3凸目 未凸

という意味になります


### ボス情報
現在攻撃可能なボスを表示します

### 攻撃中
攻撃中のプレイヤーを表示します

### 持越
持ち越しを持っているプレイヤーの数を表示します
* フル：90秒
* 長：70～89秒
* 中：40～69秒
* 短：20～39秒

### 残凸数
残り凸数を表示します  

### 予約
予約しているメンバーの一覧を表示します

# サーバ導入

導入したいサーバに「凸報告」「状況報告」の名前のチャンネルを作ります  

discord.pyを導入します  
tokenkeycode.py というファイルを作り、以下の行を記述します

```
# tokenkeycode.py というファイル名で以下の行を保存する 
# TOKEN = 'xxxxxxxxxxxxxxxxxxxxxxxx.yyyyyy.zzzzzzzzzzzzzzzzzzzzzzzzzzz'
```

discordbot.py を実行します

