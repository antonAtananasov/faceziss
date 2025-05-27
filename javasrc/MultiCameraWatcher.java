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
import java.util.*;

public class MultiCameraWatcher {

    private final CameraManager cameraManager;
    private final Handler backgroundHandler;

    private final Map<String, int[][][]> latestFrames = new HashMap<>();
    private final Map<String, CameraDevice> openCameras = new HashMap<>();

    public MultiCameraWatcher(Context context) {
        cameraManager = (CameraManager) context.getSystemService(Context.CAMERA_SERVICE);

        HandlerThread thread = new HandlerThread("CameraWatcherThread");
        thread.start();
        backgroundHandler = new Handler(thread.getLooper());

        try {
            for (String cameraId : cameraManager.getCameraIdList()) {
                openCamera(cameraId);
            }
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }

    private void openCamera(String cameraId) throws CameraAccessException {
        CameraCharacteristics characteristics = cameraManager.getCameraCharacteristics(cameraId);
        Size[] sizes = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                .getOutputSizes(ImageFormat.YUV_420_888);

        Size smallestSize = sizes[0];
        for (Size size : sizes) {
            if (size.getWidth() * size.getHeight() < smallestSize.getWidth() * smallestSize.getHeight()) {
                smallestSize = size;
            }
        }

        ImageReader imageReader = ImageReader.newInstance(
                smallestSize.getWidth(),
                smallestSize.getHeight(),
                ImageFormat.YUV_420_888,
                2);

        imageReader.setOnImageAvailableListener(reader -> {
            Image image = reader.acquireLatestImage();
            if (image != null) {
                int[][][] rgb = convertYUVToRGB(image);
                image.close();
                synchronized (latestFrames) {
                    latestFrames.put(cameraId, rgb);
                }
            }
        }, backgroundHandler);

        cameraManager.openCamera(cameraId, new CameraDevice.StateCallback() {
            @Override
            public void onOpened(CameraDevice camera) {
                openCameras.put(cameraId, camera);
                try {
                    CaptureRequest.Builder builder = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                    builder.addTarget(imageReader.getSurface());

                    camera.createCaptureSession(
                            java.util.List.of(imageReader.getSurface()),
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
                                    System.err.println("Camera session config failed: " + cameraId);
                                }
                            },
                            backgroundHandler);
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
        }, backgroundHandler);
    }

    public String[] getCameraIdList() throws CameraAccessException {
        return cameraManager.getCameraIdList();
    }

    // Returns latest frame from one camera by index
    public int[][][] getFrame(int index) throws CameraAccessException {
        String[] cameraIds = cameraManager.getCameraIdList();
        if (index < 0 || index >= cameraIds.length)
            return null;
        synchronized (latestFrames) {
            return latestFrames.get(cameraIds[index]);
        }
    }

    // Get all frames as a list
    public List<int[][][]> getAllFrames() throws CameraAccessException {
        List<int[][][]> frames = new ArrayList<>();
        String[] cameraIds = cameraManager.getCameraIdList();
        synchronized (latestFrames) {
            for (String id : cameraIds) {
                int[][][] frame = latestFrames.get(id);
                frames.add(frame); // may be null if not yet received
            }
        }
        return frames;
    }

    // Manual YUV420 to RGB
    private int[][][] convertYUVToRGB(Image image) {
        int width = image.getWidth();
        int height = image.getHeight();

        Image.Plane[] planes = image.getPlanes();
        ByteBuffer yBuffer = planes[0].getBuffer();
        ByteBuffer uBuffer = planes[1].getBuffer();
        ByteBuffer vBuffer = planes[2].getBuffer();

        int yRowStride = planes[0].getRowStride();
        int uvRowStride = planes[1].getRowStride();
        int uvPixelStride = planes[1].getPixelStride();

        int[][][] rgb = new int[height][width][3]; // R, G, B

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int yIndex = y * yRowStride + x;
                int uvIndex = (y / 2) * uvRowStride + (x / 2) * uvPixelStride;

                int Y = yBuffer.get(yIndex) & 0xFF;
                int U = (uBuffer.get(uvIndex) & 0xFF) - 128;
                int V = (vBuffer.get(uvIndex) & 0xFF) - 128;

                int R = Y + (int) (1.370705f * V);
                int G = Y - (int) (0.337633f * U + 0.698001f * V);
                int B = Y + (int) (1.732446f * U);

                rgb[y][x][0] = clamp(R);
                rgb[y][x][1] = clamp(G);
                rgb[y][x][2] = clamp(B);
            }
        }

        return rgb;
    }

    private int clamp(int value) {
        return Math.max(0, Math.min(255, value));
    }
}
