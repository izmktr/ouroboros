# 2021年7月クランバトル用ユカリさん project code:ouroboros

プリンセスコネクト:Re Diveのクランバトル用discord botです  

# コマンド
凸報告のチャンネルで入力します  

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

## 情報系

### サイコロ/dice

100面体サイコロを振ります

### 


### history
history [名前]

名前を入れた人の凸履歴を見ます  
名前を省略すると自分の凸履歴を見ます

### active
active

1時間以内に書き込みを行ったメンバーを表示します  


## メンバー管理系

### setmemberrole

setmemberrole [ロール名]

ロール名のロールを持つメンバー全員を登録メンバーにします  
全員を登録メンバーにするには @everyone を指定します

### memberdelete
memberdelete [名前]

登録メンバーから指定したメンバーを削除します

### memberinitialize
memberinitialize
すべての登録メンバーを削除します



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

### settingreload
setting.jsonを読み込み直します


# サーバ導入

