# PyPy JIT 最適化ガイド: Brainfuck インタプリタを例に

このドキュメントでは、RPython で書かれた Brainfuck インタプリタに PyPy の JIT コンパイラを適用し、段階的に最適化していく方法を解説します。

## 目次

1. [トレーシング JIT の基礎](#1-トレーシング-jit-の基礎)
2. [jit_merge_point と can_enter_jit](#2-jit_merge_point-と-can_enter_jit)
3. [JIT ヒントによる最適化](#3-jit-ヒントによる最適化)
4. [Virtualizable による最適化](#4-virtualizable-による最適化)
5. [まとめ](#5-まとめ)

---

## 1. トレーシング JIT の基礎

### トレーシング JIT とは？

tracing (トレーシング) Just-in-Time (JIT) コンパイルは、プログラムの実行を監視し、頻繁に実行されるプログラム片 (**ホットスポット**) を検出してネイティブコードにコンパイルする技術です。一般的な実行フローは以下のようになります：

1. インタプリタがコードを実行
2. JIT がプログラム片の実行回数をカウント
    - tracing JIT の場合はループの実行回数をカウントすることが多い
3. 閾値を超えると「ホット」と判定
4. ホットスポットをトレース (実行履歴を記録)
5. トレースをネイティブコードにコンパイル
6. 次回以降、コンパイル済みコードを実行

従来のメソッド単位の method JIT と異なり、tracing JIT は実際の実行パスを追跡しコンパイルします。
これにより、ループ内で実際に使われる分岐のみが最適化され、使われない分岐のコンパイルコストを避けられます。

---

## 2. jit_merge_point と can_enter_jit

### JitDriver の設定

```python
from rpython.rlib.jit import JitDriver

jitdriver = JitDriver(
    greens=['pc', 'program', 'bracket_map'],  # ループの「形」を決める変数
    reds=['tape'],                             # ループ内で変化する変数
)
```

#### greens
- ループの「アイデンティティ」を決定する変数
- 同じ green 値の組み合わせ = 同じループ
- 例: `pc`（プログラムカウンタ）、`program`（プログラム本体）

#### reds
- ループの各イテレーションで変化する変数
- 例: `tape`（Brainfuck のテープ）

### jit_merge_point

```python
while pc < len(program):
    jitdriver.jit_merge_point(
        pc=pc, tape=tape, program=program, bracket_map=bracket_map
    )
    # ... インタプリタのメインロジック
```

`jit_merge_point` は JIT に「ここがループの先頭です」と伝えます：

```
      jit_merge_point ←── ここでトレースを開始/マージ
            │
            ▼
    ┌───────────────┐
    │ ループ本体     │
    │ (命令の実行)   │
    └───────┬───────┘
            │
            ▼
         pc += 1
            │
            └──────────→ ループの先頭へ
```

### can_enter_jit

```python
elif code == "]":
    if tape.get() != 0:
        pc = bracket_map[pc]  # 後方ジャンプ
        jitdriver.can_enter_jit(
            pc=pc, tape=tape, program=program, bracket_map=bracket_map
        )
```

`can_enter_jit` は「ここで既にコンパイル済みのトレースに入れます」と伝えます。

#### なぜ後方ジャンプで必要なのか？

```
Brainfuck のループ構造:

    [  ────────────────────────────────   →]
    ↑                                      │
    │         tape.get() != 0 の場合       │
    └──────────────────────────────────────┘
              （後方ジャンプ）

この後方ジャンプが can_enter_jit の場所
```

後方ジャンプ（バックエッジ）はループの繰り返しを意味します。JIT はこの地点で：
1. プログラム片 (ループ) が「ホット」かどうかを判定
2. コンパイル済みトレースがあれば、そこにジャンプ

---

## 3. JIT ヒントによる最適化

### @elidable デコレータ

```python
from rpython.rlib.jit import elidable

@elidable
def get_bracket_target(bracket_map, pc):
    return bracket_map.get(pc, -1)
```

`@elidable` は「この関数は純粋関数です」と JIT に伝えます：
- 同じ入力には常に同じ出力
- 副作用なし

**効果**: JIT は同じ引数での呼び出し結果をキャッシュし、冗長な計算を省略できます。

```
最適化前:
    bracket_map[pc] → ハッシュテーブル検索 → 結果

最適化後（pcが定数の場合）:
    定数値として直接埋め込み
```

### promote() ヒント

```python
from rpython.rlib.jit import promote

def mainloop(program, bracket_map):
    program = promote(program)  # 実行時の値をコンパイル時定数に昇格
    # ...
```

`promote()` は「この変数はループ中に変化しないので、定数として扱ってよい」と JIT に伝えます。

**効果**: `program[pc]` のようなアクセスが、直接的な定数参照になります。

### @unroll_safe デコレータ

```python
from rpython.rlib.jit import unroll_safe

@unroll_safe
def parse(program):
    for char in program:
        # ...
```

通常、JIT は未知の回数のループを安全にアンロール（展開）しません。`@unroll_safe` は「このループは安全にアンロールできます」と伝えます。

---

## 4. Virtualizable による最適化

### Virtualizable とは？

```python
class Tape(object):
    _virtualizable_ = ['position', 'thetape[*]']

    def __init__(self):
        self = hint(self, access_directly=True, fresh_virtualizable=True)
        self.thetape = [0] * 30000
        self.position = 0
```

`_virtualizable_` は JIT に「このオブジェクトのフィールドを仮想化してよい」と伝えます。

### 仮想化の効果

```
通常のオブジェクト:
┌─────────────────────────────────┐
│ ヒープメモリ                     │
│  ┌─────────────────────┐        │
│  │ Tape オブジェクト    │        │
│  │  position: 42       │        │
│  │  thetape: [...]     │        │
│  └─────────────────────┘        │
└─────────────────────────────────┘
       ↑
       │ メモリアクセス（遅い）
       │
    CPU レジスタ


Virtualizable の場合:
┌─────────────────────────────────┐
│ CPU レジスタ                     │
│  r1 = position (42)             │
│  r2 = thetape のベースアドレス   │
└─────────────────────────────────┘
       ↓
       直接アクセス（高速）
```

JIT はホットループ内でオブジェクトをヒープに割り当てる代わりに、フィールドを直接レジスタに保持できます。これにより：

- メモリアロケーションの削減
- キャッシュミスの削減
- 高速なフィールドアクセス

### 配列の Virtualizable

```python
_virtualizable_ = ['position', 'thetape[*]']
```

`thetape[*]` の `[*]` は「この配列の要素も仮想化対象」という意味です。JIT は配列アクセスを最適化し、インデックスが定数の場合は直接的なレジスタ操作に変換できます。

---

## 5. まとめ

### 最適化の階層

```
レベル 1: 基本的な JIT
├── JitDriver の設定
├── jit_merge_point の配置
└── can_enter_jit の配置

レベル 2: ヒントによる最適化
├── @elidable（純粋関数の宣言）
├── promote()（定数への昇格）
└── @unroll_safe（ループ展開の許可）

レベル 3: 高度な最適化
├── Virtualizable（オブジェクトの仮想化）
├── 固定サイズ配列の使用
└── メモリアクセスパターンの最適化
```

### 最適化のベストプラクティス

1. **まず動くコードを書く**
   - 最適化は後から追加できる

2. **プロファイリングで hotspot を特定**
   - 実際に遅い部分を見つける

3. **green/red 変数を慎重に選ぶ**
   - green が多すぎると、トレースが増えすぎる
   - red が多すぎると、最適化の機会を逃す

4. **can_enter_jit を忘れない**
   - 後方ジャンプには必ず配置

5. **Virtualizable は慎重に使う**
   - 効果は大きいが、設定を間違えるとバグの原因に

### 参考資料

- [PyPy Documentation](https://doc.pypy.org/)
- [RPython JIT Documentation](https://rpython.readthedocs.io/en/latest/jit/)
- [PyPy Tutorial (Original)](https://morepypy.blogspot.com/2011/04/tutorial-writing-interpreter-with-pypy.html)
