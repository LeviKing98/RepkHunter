# RepkHunter

A tool used to detect repackaged APKs. It is specifically designed for anti-obfuscation purposes.

# SetUp
1. install the Java Runtime Environment (JRE) and Java Decompiler (baksmali) on your system.
    - baksmali.jar and baksmali are required to decompile APKs. You can download them from [baksmali.jar](https://github.com/baksmali/smali/releases) and [baksmali](https://github.com/baksmali/smali/blob/main/scripts/baksmali). They should be set in the directory under ./scripts.

    - Java is required to run baksmali. You can download it from [here](https://www.oracle.com/java/technologies/javase-downloads.html).

2. Install the required Python packages.
    ```bash
    pip install -r requirements.txt
    ```

# Usage

Provide the paths to `apk1` and `apk2`. RepkHunter will output a similarity score for the APK pair.

```bash
cd ./scripts/
python RepkHunter.py ./example/apk1 ./example/apk2
```

The output will be a similarity score between 0 and 1, where 1 indicates a perfect match.
```
Similarity score:0.9864253393665159
```
# Dataset
The dataset used in this project is available at [here](https://drive.google.com/file/d/1-3h33h33h33h33h33h33h33h33h33h3/view?usp=share_link).

You can use obfuscators to obfuscate the APKs in the dataset.