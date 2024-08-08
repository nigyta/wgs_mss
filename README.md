# MSSmaker
多数のゲノム塩基配列を一括で DDBJ の登録形式に変換するスクリプトです。生成した登録形式ファイルは DDBJ MSS (Mass Submission System, 大量登録システム) を使って登録することができます。  
エクセルファイルまたはタブ区切り表形式ファイル (tsvファイル) の各行にゲノム塩基配列の FASTA 形式ファイルへのパスおよび各ゲノムについてのメタデータ (生物種名、他) を記載して、MSS 形式ファイルへの変換を行います。  
塩基配列中にギャップ (NNN...) が存在する場合、`assebmly_gap` フィーチャーとして記載されます。その際に、`gap_type` や `linkage_evidence` の値については、全て同一の値が記載されます ([後述](#assembly_gap-の記載について))。  
`CDS` などの biological feature の記載 (アノテーションの記述) はできません。本スクリプトはアノテーションなしでゲノム塩基配列情報のみを DDBJ に登録するためのものです。アノテーションされた原核生物ゲノムの登録には DFAST をご使用ください ([web](https://dfast.ddbj.nig.ac.jp), [github](https://github.com/nigyta/dfast_core))。
completeゲノムの登録には対応していません (真核生物の場合には染色体名の指定、原核生物の場合には染色体/plasmidの指定を配列ごとに行う必要があるため)。

## 入力ファイル (必須)
- FASTAファイルへのパスを含んだエクセルファイル (xlsx) またはタブ区切り表形式ファイル (tsv)  
    エクセルファイルの場合`--excel`、tsvファイルの場合 `--tsv`で指定。エクセルファイルを指定した場合、`--sheet` で読み込むワークシートを指定できる (デフォルトは "Sheet1")  
	Excelファイルではすべてのセルが文字列として記載されるように注意してください。数値や日付データとして記載されていた場合、正しく処理がされない可能性があります。そのため、tsv形式のファイルを指定することを推奨します。　　
    1, 2行目はヘッダー。各行の一列目にはFASTAファイルへのパス (絶対パスまたはスクリプトを実行するディレクトリからの相対パス) を記載、二列目には登録区分を記載、3行目に各サンプル固有のメタデータを記載する。  
    記載できるメタデータについては[後述](#記載できるメタデータ)  
    例) [example/sample_list.xlsx](example/sample_list.xlsx), [example/sample_list_WGS.tsv](example/sample_list_WGS.tsv), [example/sample_list_MAG.tsv](example/sample_list_MAG.tsv)  

- メタデータテンプレートファイル  
    `--metadata_json_file` または `-m` で指定  
    全データに共通するメタデータを記載 (submitter や reference 情報など)  
    ファイルの形式はMSS登録形式ファイル (タブ区切りの５列の表形式ファイル) の内容を JSON 形式で記述したもの。記載形式や記述できる内容についてはMSS登録ファイルの作成マニュアル ([submitter](https://www.ddbj.nig.ac.jp/ddbj/file-format.html#submitter)、[reference](https://www.ddbj.nig.ac.jp/ddbj/file-format.html#reference)) を参考。  
    例) [example/common_example.json](example/common_example.json)

## オプション
- `-o` または `--out_dir`: 結果ファイルの出力先ディレクトリを指定。デフォルトはカレントディレクトリ  
- `-H` or `--hold_date` でデータの公開予定日(hold_date)を年月日の順で、半角数字８桁(例：20250506)で指定。登録完了後に即時公開を希望する場合、指定不要  

- ギャップの指定について  
配列中に N で表される塩基配列を決定できなかった領域 (ギャップ領域) がある場合、__assembly_gap__ フィーチャーが記載されます。記載方法については
`--linkage_evidence`、`--gap_type`、`--gap_length`、`--min_gap_length`の各オプションで指定できます。詳細は [assembly_gap の記載について](#assembly_gap-の記載について) を参照ください。配列中にギャップが含まれない場合、これらのオプションの指定は無視されます。  

## 実行環境
Python 3.11 以降  
Biopython, pandas, openpyxl, jsonschema モジュールが必要。以下でインストールできます。
```
pip install biopython pandas openpyxl jsonschema
または
conda install -c bioconda biopython
conda install pandas openpyxl jsonschema
```

## 使用例

```
# ソースコード取得
git clone https://github.com/nigyta/wgs_mss.git
cd wgs_mss

# テスト用データ取得
./example/prepare_test_data.sh

# 実行
./MSSmaker.py --tsv example/sample_list_MAG.tsv -m example/common_example.json -o OUT
./MSSmaker.py --excel example/sample_list.xlsx --sheet MAG -m example/common_example.json -o OUT -H 20260501

```

## assembly_gap の記載について
このスクリプトでは10塩基分以上の `N` が続いた領域をギャップとみなして `assembly_gap` フィーチャーを記載します。ギャップとみなす最小の塩基数は、`--min_gap_length` で指定可能ですが、特に理由がない限りこの値を変更しないでください。  

デフォルトでは `gap_type` = "within scaffold", `linkage_evidence` = "paired-ends", 推定長については "known" が記載されます。  
これらは、`--gap_type`、`--linkage_evidence`、`--gap_length` で指定可能です。  
指定した値は、すべてのファイルのギャップ領域について共通して記載されます。異なる種類の `gap_type` や `linkage_evidence` が含まれる場合はこのスクリプトではデータ変換を行うことができません。  
一般には下記のような値を指定します。
- ペアエンドリードを利用してscaffoldingを行った場合: `linkage_evidence` = "paired-ends"、`--gap_type` = "within_scaffold"、`--gap_length` = "known"  
- HiC でscaffolding を行った場合:  `linkage_evidence` = "proximity_ligation"、`--gap_type` = "within_scaffold"、`--gap_length` = "unknown"  
- 近縁種へのアラインメントによって scaffolding を行った場合:  `linkage_evidence` = "align_genus"、`--gap_type` = "within_scaffold"、`--gap_length` = "unknown"  
上記の３種類については `--linkage_evidence` のみ指定すれば `--gap_type`と`--gap_length`は自動で設定されます。  

記載例

```
sequence01	assembly_gap	684943..685144	estimated_length	known
			gap_type	within scaffold
			linkage_evidence	paired-ends
```

## 記載できるメタデータ
ゲノム塩基配列の場合、BioProject、BioSample IDは必須です。また、MAGの場合、SRAのリードアクセッションも必要となります。記載できるメタデータの代表的な例はサンプルファイルをご参照ください。  
配列の生物的由来を示す情報 (__source__フィーチャー)については任意の項目を付け足すことが可能です。その場合にはサンプルシートのヘッダー１行目には `source`、２行目には属性 (qualifier)名を記載してください。sourceフィーチャーに使用できるqualifierについてはこちらの[対応表](https://docs.google.com/spreadsheets/d/1qosakEKo-y9JjwUO_OFcmGCUfssxhbFAm5NXUAnT3eM/edit?gid=0#gid=0)をご参照ください。　　

## 生成される登録ファイルの例
五列のタブ区切り表形式ファイルが出力されます。(画面上ではずれて見える場合があります)
```
COMMON	DIVISION		division	ENV
	DATATYPE		type	WGS
	KEYWORD		keyword	WGS
			keyword	STANDARD_DRAFT
			keyword	ENV
			keyword	MAG
			keyword	Metagenome Assembled Genome
	DBLINK		project	PRJDB99999
			biosample	SAMD999998
			sequence_read_archive	DRR999998
	SUBMITTER		ab_name	Tanizawa,Y.
			ab_name	Doe,J.
			ab_name	Smith,Y.
			contact	Yasuhiro Tanizawa
			email	dfast@ddbj.nig.ac.jp
			phone	81-99-999-9999
			institute	National Institute of Genetics
			department	Bioscience and DDBJ Center
			country	Japan
			state	Shizuoka
			city	Mishima
			street	Yata 1111
			zip	411-8540
	REFERENCE		title	Genome analysis of XXXXX XXXXXX
			ab_name	Tanizawa,T.
			ab_name	Doe,J.
			ab_name	Smith,Y.
			status	Unpublished
			year	2024
	ST_COMMENT		tagset_id	Genome-Assembly-Data
			Assembly Method	Megahit v. 1.0
			Genome Coverage	120x
			Sequencing Technology	Illumina NovaSeq
	COMMENT		Data 2	Data 2
			 Data 2, line2	Data 2, line2
	DATE		hold_date	20240626
	source	1..E	mol_type	genomic DNA
			organism	Clostridium zea
			strain	CSC2
			country	Japan
			collection_date	20230422
			submitter_seqid	@@[entry]@@
			ff_definition	@@[organism]@@ @@[strain]@@ DNA, draft genome: @@[entry]@@
sequence01	assembly_gap	1906369..1906657	estimated_length	known
			gap_type	within scaffold
			linkage_evidence	paired-ends
```