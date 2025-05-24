#!/bin/sh
#run with "source" command
buildozer android debug && \
adb install ./bin/faceziss-0.1-arm64-v8a_armeabi-v7a-debug.apk && \
adb shell monkey -p "org.tonziss.faceziss" -c android.intent.category.LAUNCHER 1 && \
adb logcat | grep "I python"