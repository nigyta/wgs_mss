# MSSmaker
多数のゲノム塩基配列を一括で DDBJ の登録形式に変換するスクリプトです。生成した登録形式ファイルは DDBJ MSS (Mass Submission System, 大量登録システム) を使って登録することができます。  
タブ区切り表形式ファイル (tsvファイル) の各行にゲノム塩基配列の FASTA 形式ファイルへのパスおよび各ゲノムについてのメタデータ (生物種名、他) を記載して、MSS 形式ファイルへの変換を行います。  
塩基配列中にギャップ (NNN...) が存在する場合、`assebmly_gap` フィーチャーとして記載されます。その際に、`gap_type` や `linkage_evidence` の値については、全て同一の値が記載されます ([後述](#assembly_gap-の記載について))  
`CDS` などの biological feature の記載 (アノテーションの記述) はできません。本スクリプトはアノテーションなしでゲノム塩基配列情報のみを DDBJ に登録するためのものです。アノテーションされた原核生物ゲノムの登録には DFAST をご使用ください ([web](https://dfast.ddbj.nig.ac.jp), [github](https://github.com/nigyta/dfast_core))。

## 入力ファイル
- FASTAファイルへのパスを含んだタブ区切り表形式ファイル  
    `--fasta_list` or `-f`で指定  
    一行目はヘッダー。各行の一列目にはFASTAファイルへのパス (絶対パスまたはスクリプトを実行するディレクトリからの相対パス) を記載、二列目以降は登録に必要なメタデータを記載  
    記載できるメタデータについては[後述](#記載できるメタデータ)  
    例) [example/file_list_example.tsv](example/file_list_example.tsv)  

- メタデータテンプレートファイル  
    `--metadata_file` or `-m` で指定  
    全データに共通するメタデータを記載 (submitterやreference情報など)  
    MSS登録ファイルの作成マニュアル ([submitter](https://www.ddbj.nig.ac.jp/ddbj/file-format.html#submitter)、[reference](https://www.ddbj.nig.ac.jp/ddbj/file-format.html#reference)) を参考。五列のうち一列目の値は空欄にしておくこと。  
    例) [example/metadata_wgs_example.tsv](example/metadata_wgs_example.tsv)

## 実行環境
Python 3.7 以降  
Biopython が必要。以下でインストール
```
pip install biopython
または
conda install -c bioconda biopython
```

## 使用例

```
# ソースコード取得
git clone https://github.com/nigyta/wgs_mss.git
cd wgs_mss

# テスト用データ取得
cd example
./prepare_test_data.sh

# 実行
../MSSmaker.py -f file_list_example.tsv -m metadata_wgs_example.tsv -o ./ --category draft_mag --hold_date 20250506 --rename_sequence
```

- `-c` or `--category` で登録するデータのカテゴリを {draft_genome,draft_mag,complete_genome,complete_mag} の中から選んで指定する (**必須**)。指定したカテゴリに応じて登録ファイルに記載する DATATYPE や KEYWORD 等が決まる。  
- `-o` or `--outdir` で出力ファイルの生成先ディレクトリを指定  
- `-H` or `--hold_date` でデータの公開予定日(hold_date)を年月日の順で、半角数字８桁(例：20250506)で指定。登録完了後に即時公開を希望する場合、指定不要  
- `-ｒ` or `--rename_sequence` を指定すると、配列名を`sequence01`、`sequence02` ... という名称に変更して登録する。指定しない場合、FASTAファイル中に記載された配列ID (ヘッダ行の最初のスペースまで)が配列名として使われる。配列名はデータ公開ファイルのDEFINITION行と source フィーチャー (配列の由来についての記載項目) に `submitter_seqid` として記載される。  

## assembly_gap の記載について
このスクリプトでは10塩基分以上の `N` が続いた領域をギャップとみなして `assembly_gap` フィーチャーを記載します。この値は、`--min_gap_length` で指定可能ですが、特に理由がない限りこの値を変更しないでください。  
デフォルトでは `gap_type` = "within scaffold", `linkage_evidence` = "paired-ends", 推定長については "known" が記載されます。  
これらは、`--gap_type`、`--linkage_evidence`、`--gap_length` で指定可能です。  
指定した値は、すべてのファイルのギャップ領域について共通して記載されます。異なる種類の `gap_type` や `linkage_evidence` が含まれる場合はこのスクリプトではデータ変換を行うことができません。

記載例

```
sequence01	assembly_gap	684943..685144	estimated_length	known
			gap_type	within scaffold
			linkage_evidence	paired-ends
```

## 記載できるメタデータ
BioSample IDや、生物種名、株名等の各ゲノムで異なるメタデータについては、FASTAファイルの一覧表に記載します。  
メタデータの項目名は一覧表のヘッダー行に記載された値が使用されます。  
__to be updated.__

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
			Assembly Method	Megahit v. 1
			Genome Coverage	120x
			Sequencing Technology	Illumina NovaSeq
	COMMENT		Data 2	Data 2
			 Data 2, line2	Data 2, line2
	DATE		date	20240626
	source	1..E	mol_type	genomic DNA
			organism	Clostridium zea
			strain	CSC2
			country	Japan
			collection_date	20230422
			submitter_seqid	@@[entry]@@
			ff_definition	@@[entry]@@
sequence01	assembly_gap	1906369..1906657	estimated_length	known
			gap_type	within scaffold
			linkage_evidence	paired-ends
```