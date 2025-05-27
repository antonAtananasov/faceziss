package org.faceziss;

import android.content.Context;
import android.graphics.ImageFormat;
import android.hardware.camera2.*;
import android.media.Image;
import android.media.ImageReader;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Size;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;

public class MultiCameraCapture {
    private final CameraManager cameraManager;
    private final Context context;
    private final Handler backgroundHandler;

    public MultiCameraCapture(Context context) {
        this.context = context;
        this.cameraManager = (CameraManager) context.getSystemService(Context.CAMERA_SERVICE);

        HandlerThread thread = new HandlerThread("CameraBackground");
        thread.start();
        this.backgroundHandler = new Handler(thread.getLooper());
    }

    public List<byte[][][]> captureFromAllCameras() throws Exception {
        String[] cameraIds = cameraManager.getCameraIdList();
        List<byte[][][]> rgbFrames = new ArrayList<>();

        for (String cameraId : cameraIds) {
            CameraCharacteristics characteristics = cameraManager.getCameraCharacteristics(cameraId);
            Size[] sizes = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                    .getOutputSizes(ImageFormat.YUV_420_888);
            Size chosenSize = sizes[0];

            ImageReader reader = ImageReader.newInstance(
                    chosenSize.getWidth(),
                    chosenSize.getHeight(),
                    ImageFormat.YUV_420_888,
                    2);

            final Object lock = new Object();
            final byte[][][][] rgbOut = new byte[1][][][]; // Only one 3D image

            reader.setOnImageAvailableListener(readerListener -> {
                Image image = readerListener.acquireLatestImage();
                if (image != null) {
                    rgbOut[0] = convertYUVToRGB(image);
                    image.close();
                    synchronized (lock) {
                        lock.notify();
                    }
                }
            }, backgroundHandler);

            CameraDevice.StateCallback deviceCallback = new CameraDevice.StateCallback() {
                @Override
                public void onOpened(CameraDevice camera) {
                    try {
                        CaptureRequest.Builder builder = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                        builder.addTarget(reader.getSurface());

                        camera.createCaptureSession(List.of(reader.getSurface()),
                                new CameraCaptureSession.StateCallback() {
                                    @Override
                                    public void onConfigured(CameraCaptureSession session) {
                                        try {
                                            session.setRepeatingRequest(builder.build(), null, backgroundHandler);
                                        } catch (CameraAccessException e) {
                                            e.printStackTrace();
                                        }
                                    }

                                    @Override
                                    public void onConfigureFailed(CameraCaptureSession session) {
                                        System.err.println("Session config failed.");
                                    }
                                }, backgroundHandler);

                    } catch (CameraAccessException e) {
                        e.printStackTrace();
                    }
                }

                @Override
                public void onDisconnected(CameraDevice camera) {
                    camera.close();
                }

                @Override
                public void onError(CameraDevice camera, int error) {
                    camera.close();
                }
            };

            synchronized (lock) {
                cameraManager.openCamera(cameraId, deviceCallback, backgroundHandler);
                lock.wait(3000); // wait for frame
            }

            if (rgbOut[0] != null) {
                rgbFrames.add(rgbOut[0]); // add 3D image to list
            }
        }

        return rgbFrames;
    }

    private byte[][][] convertYUVToRGB(Image image) {
        int width = image.getWidth();
        int height = image.getHeight();

        Image.Plane[] planes = image.getPlanes();
        ByteBuffer yBuffer = planes[0].getBuffer();
        ByteBuffer uBuffer = planes[1].getBuffer();
        ByteBuffer vBuffer = planes[2].getBuffer();

        int yRowStride = planes[0].getRowStride();
        int uvRowStride = planes[1].getRowStride();
        int uvPixelStride = planes[1].getPixelStride();

        byte[][][] rgbArray = new byte[height][width][3];

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int yIndex = y * yRowStride + x;
                int uvIndex = (y / 2) * uvRowStride + (x / 2) * uvPixelStride;

                int Y = yBuffer.get(yIndex) & 0xFF;
                int U = (uBuffer.get(uvIndex) & 0xFF) - 128;
                int V = (vBuffer.get(uvIndex) & 0xFF) - 128;

                int R = (int) (Y + 1.370705f * V);
                int G = (int) (Y - 0.337633f * U - 0.698001f * V);
                int B = (int) (Y + 1.732446f * U);

                R = Math.max(0, Math.min(255, R));
                G = Math.max(0, Math.min(255, G));
                B = Math.max(0, Math.min(255, B));

                rgbArray[y][x][0] = (byte) R;
                rgbArray[y][x][1] = (byte) G;
                rgbArray[y][x][2] = (byte) B;
            }
        }

        return rgbArray;
    }
}
