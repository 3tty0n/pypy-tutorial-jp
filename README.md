# Tutorial: Writing an Interpreter with RPython/PyPy
This is a copy of a source code of [a guest blog post by Andrew Brown](https://pypy.org/posts/2011/04/tutorial-writing-interpreter-with-pypy-3785910476193156295.html#), which was originally posted to the pypy-dev mailing list.
The original source code of this tutorial was hosted on Bitbucket, but it is no longer available in 2024.
This version has been reproduced to serve as educational material for lab interns at the [PRG-lab](https://prg.is.titech.ac.jp/) of Institute of Science Tokyo (from September 2024, formerly Tokyo Institute of Technology).

本リポジトリは、pypy-devメーリングリストに投稿された[Andrew Brownによるゲストブログ記事](https://pypy.org/posts/2011/04/tutorial-writing-interpreter-with-pypy-3785910476193156295.html#)に付随するサンプルコードを復元したものです。2024年時点でBitbucket上の元リポジトリは取得できないため、教育目的で再構成しました。
東京科学大学[プログラミング研究室](https://prg.is.titech.ac.jp/)の4日間インターン課題として利用しています。

## Schedule
- Day 1: [Tutorial: Writing an Interpreter with PyPy, Part 1](https://pypy.org/posts/2011/04/tutorial-writing-interpreter-with-pypy-3785910476193156295.html#)を読む
- Day 2: [Tutorial Part 2: Adding a JIT](https://pypy.org/posts/2011/04/tutorial-part-2-adding-jit-8121732841568309472.html)を読む
- Day 3, Day 4: BFインタプリタのJITコンパイラを最適化する、または [PyPyの論文](https://doc.pypy.org/en/latest/extradoc.html)を読む
- Day 5 (, Day 6): (自習) 発表スライド準備

## Requirements
- Python 2（RPythonはPython 2で記述されているため、Python 3では構文エラーになります）
- RPython（PyPyリポジトリ同梱のものを使用）

## Installation
`rpython`を含む`pypy`ディレクトリをサブモジュールとして取得します。`--recursive`を忘れると`pypy/`が不足します。
```sh
git clone --recursive git@github.com:3tty0n/pypy-tutorial-jp.git
```

## 旧情報との差分
### `pypy` 及び `rpython` の差分管理方法の変更
Part 1 - Translating 内の `hg clone https://bitbucket.org/pypy/pypy` は古い情報です。
`rpython` は 2024年10月時点で GitHub 管理の pypy リポジトリ内 `pypy/rpython/bin/rpython` に配置されています。

サブモジュールを使わず手動で導入する場合は、以下のように読み替えてください（上記インストール手順を取った場合は不要です）。
```sh
git clone https://github.com/pypy/pypy
  ```

### `rpython` で BF インタプリタを変換
Part 1最終節およびPart 2に記載の translator 実行パスは古いため、`/pypy/pypy/translator/goal/translate.py` を `./pypy/rpython/bin/rpython` に読み替えてください。インタプリタ`(your interpreter).py`を変換するには次を実行します。`--opt=jit` を付けると変換先 `(your interpreter)-c` にJITコンパイラが含まれます。

```sh
# インタプリタをC言語経由でネイティブコードへ変換
python2 ./pypy/rpython/bin/rpython -O2 (your interpreter).py

# インタプリタをC言語経由でネイティブコードへ変換かつメタトレーシングJITコンパイラを適用
python2 ./pypy/rpython/bin/rpython -Ojit (your interpreter).py
```

### 他注意点
- ["Download and Install"](https://pypy.org/download.html) で配布されている prebuild バイナリには `rpython` は含まれません。
- RPython は **Python 2** で書かれているため、Python 3で実行すると構文エラーになります。
  - [pyenv](https://github.com/pyenv/pyenv) を使うと Python 2/3 を切り替えやすくなります。
  ```sh
  pyenv local x.y.z
  ```

## トレースを見る方法
JITコンパイラが生成したトレースを確認する手順です。以下のコマンドを実行すると、100個の `A` が出力され、同時にログが保存されます。
```
PYPYLOG=jit-log-opt:logfile ./example5-c test100.b
```
`logfile` にコンパイル済みトレースが記録されます。一般に内側の2つのループが `Loop1` と `Loop2` として現れます（どちらがどちらかは状況次第）。命令列を眺めて不要な命令が残っていないか確認します。
命令名の意味の目安:
- `int_add` とか `int_sub` とかは明らかだろうと思います。
- `setarrayitem_gc`, `getarrayitem_gc` とかは配列の読み書き
- `setfield_gc`, `getfield_gc` はオブジェクトのフィールドの読み書き (フィールド名が引数に出現しているはず)
です。

インタプリタで `green` とした `pc`、`program`、`bracket_map` に関する命令がトレース内に残っている場合は、コード品質が十分でない可能性があります。

トレース時間や命令数などの統計を出力する `jit-summary`、生成機械語を出力する `jit-backend` も `PYPYLOG` で指定できます。

以下のように指定すると複数のプロファイル情報をまとめて出力することができます。

```
PYPYLOG=jit-log-opt,jit-backend,jit-summary:logfile ./example5-c test100.b
```

全てのプロファイル情報を出力するには `PYPYLOG=jit:logfile` とします。

また `:` の右側に `-` を指定すると stderr に情報を出力することができます。

### jitviewer

[jitviewer](https://github.com/3tty0n/jitviewer#) は PyPy のトレースログを可視化する簡易 Web アプリケーションです。インストールと利用方法は次のとおりです。

```sh
# インストール
$ git clone https://github.com/3tty0n/jitviewer.git
$ cd jitviewer
$ pip install -r requirements.txt
$ pip install .

# 使い方 (/path/to/pypy および /path/to/tracelog は適切なパスに読み替え)
$ PYTHONPATH=/path/to/pypy jitviewer.py -l /path/to/tracelog
```


## 最適化のヒント
最適化のポイント:
- Tapeオブジェクトへのアクセスに伴うread/write回数を減らしたい
- 静的に計算できるものは静的に計算してしまいたい

### ループオーバーヘッドの除去
- オーバーヘッドの予測: ループでは pc が指す値が0になるまで guard（read/compare/assert）を繰り返すため遅くなる。
- 最適化のアイディア: ループ中に pc が移動しないパターンを BF 拡張命令として扱い、インタプリタ側で効率的に処理してループを消す。

#### 頻出パターン：set 0
ループの解釈: 今の pc の位置の値を0にし、pcはそのまま。
```
[-]
```

#### 頻出パターン：add n (Run-length encoding)
ループの解釈: 今の pc の値を3つ右のポインタに加算し（元の位置は set 0）、元の pc に戻る。
```
[->>>+<<<<]
```
```
[>>>+<<<-]
```
ループの解釈: 今の pc の値を2つ左のポインタに加算し（元の位置は set 0）、元の pc に戻る。
```
[-<I>-]
```

#### 頻出パターン：add nパターンの一般化 (Run-length encoding)
ループの解釈: 今の pc の値を1つ右、2つ右、3つ右のポインタにそれぞれ加算し（元の位置は set 0）、元の pc に戻る。
```
[->+>+>+<<<]
```
```
[>+>+>+<<<-]
```

### ループ開始位置におけるテープ位置の事前計算
要追記（未検証）

## 結果・評価
- [Part 1](https://pypy.org/posts/2011/04/tutorial-writing-interpreter-with-pypy-3785910476193156295.html#)を最後まで完了すると、以下のような出力を得ます:
```sh
./example2-c mandel.b
```
<p align="center"><img width="25%" alt="mandel.png" src="figs/mandel.png"></p>

- PyPyツールチェーンで変換されたインタプリタの速度を比較するには `evaluate.py` を実行します。
`evaluate.py` の内部では、 `example2-c`, `example3-c`, `example4-c`, `example5-c`のそれぞれを5回ずつ実行した実行時間を記録し、平均値と分散を元に結果のグラフを出力しています。
```
python3 -m venv evalenv
source evalenv/bin/activate
python3 -m pip install numpy matplotlib
python3 evaluate.py
deactivate
```
実行例：
<p align="center"><img width="80%" alt="execution_time_plot.png" src="figs/execution_time_plot.png"></p>

## RPython/PyPy を使用したインタプリタを最適化するヒント

Carl Friedrich が過去にまとめた [blog](https://pypy.org/posts/2011/03/controlling-tracing-of-interpreter-with_15-3281215865169782921.html) が参考になります。
