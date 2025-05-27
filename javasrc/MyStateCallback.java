package org.faceziss;

import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraDevice.StateCallback;

class MyStateCallback extends StateCallback {
    public MyStateCallback(){
        super();
    }

    @Override
    public void onOpened(CameraDevice camera) {
        System.out.println("Camera opened!");
    }

    @Override
    public void onDisconnected(CameraDevice camera) {
        System.out.println("Camera disconnected");
    }

    @Override
    public void onError(CameraDevice camera, int error) {
        System.out.println("Camera error: " + error);
    }

    public void sayHello() {
        System.out.println("Hello from Java!");
    }
}