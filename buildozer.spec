[app]
title = Insurance PDF Viewer
package.name = insurancepdfviewer
package.domain = org.kuldip
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = tests, bin, .buildozer, __pycache__
version = 1.0
requirements = python3,kivy==3.0.0,pdfplumber,pdfminer.six,Pillow,pycryptodome,plyer,charset-normalizer,chardet,cryptography
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, INTERNET
android.api = 34
android.minapi = 21
android.ndk = 27c
android.accept_sdk_license = True
android.archs = arm64-v8a
android.release_artifact = apk
android.debug_artifact = apk
p4a.python_recipe = python3.12

[buildozer]
log_level = 2
warn_on_root = 1
