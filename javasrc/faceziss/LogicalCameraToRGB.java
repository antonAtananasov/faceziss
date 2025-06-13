package javasrc.faceziss;

import android.content.Context;
import android.graphics.ImageFormat;
import android.hardware.camera2.*;
import android.media.Image;
import android.media.ImageReader;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;
import android.util.Size;
import android.util.SparseIntArray;
import android.view.Surface;

import java.nio.ByteBuffer;
import java.util.Arrays;

public class LogicalCameraToRGB {
    private final Context context;
    private final int width;
    private final int height;
    private CameraDevice cameraDevice;
    private CameraCaptureSession captureSession;
    private ImageReader imageReader;
    private Handler backgroundHandler;
    private HandlerThread backgroundThread;
    private String logicalCameraId;

    public interface FrameCallback {
        void onFrame(int[][][] rgbArray);
    }

    private final FrameCallback callback;

    public LogicalCameraToRGB(Context context, int width, int height, FrameCallback callback) {
        this.context = context;
        this.width = width;
        this.height = height;
        this.callback = callback;
    }

    public void startCamera() {
        startBackgroundThread();
        openCamera();
    }

    public void stopCamera() {
        if (captureSession != null) captureSession.close();
        if (cameraDevice != null) cameraDevice.close();
        if (imageReader != null) imageReader.close();
        stopBackgroundThread();
    }

    private void openCamera() {
        try {
            CameraManager manager = (CameraManager) context.getSystemService(Context.CAMERA_SERVICE);

            for (String cameraId : manager.getCameraIdList()) {
                CameraCharacteristics characteristics = manager.getCameraCharacteristics(cameraId);
                if (characteristics.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK &&
                        Arrays.asList(characteristics.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES))
                                .contains(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA)) {
                    logicalCameraId = cameraId;
                    break;
                }
            }

            if (logicalCameraId == null) {
                throw new RuntimeException("No logical camera found.");
            }

            manager.openCamera(logicalCameraId, stateCallback, backgroundHandler);
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }

    private final CameraDevice.StateCallback stateCallback = new CameraDevice.StateCallback() {
        @Override public void onOpened(CameraDevice camera) {
            cameraDevice = camera;
            startCaptureSession();
        }

        @Override public void onDisconnected(CameraDevice camera) {
            camera.close();
            cameraDevice = null;
        }

        @Override public void onError(CameraDevice camera, int error) {
            camera.close();
            cameraDevice = null;
        }
    };

    private void startCaptureSession() {
        imageReader = ImageReader.newInstance(width, height, ImageFormat.YUV_420_888, 2);
        imageReader.setOnImageAvailableListener(reader -> {
            try (Image image = reader.acquireLatestImage()) {
                if (image != null) {
                    int[][][] rgb = yuv420ToRgb(image);
                    callback.onFrame(rgb);
                    Log.i("python", "Image has size "+rgb.length+"x"+rgb[0].length );
                }
            }
        }, backgroundHandler);

        try {
            cameraDevice.createCaptureSession(
                    Arrays.asList(imageReader.getSurface()),
                    new CameraCaptureSession.StateCallback() {
                        @Override
                        public void onConfigured(CameraCaptureSession session) {
                            captureSession = session;
                            try {
                                CaptureRequest.Builder builder = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                                builder.addTarget(imageReader.getSurface());
                                builder.set(CaptureRequest.CONTROL_MODE, CameraMetadata.CONTROL_MODE_AUTO);
                                session.setRepeatingRequest(builder.build(), null, backgroundHandler);
                            } catch (CameraAccessException e) {
                                e.printStackTrace();
                            }
                        }

                        @Override public void onConfigureFailed(CameraCaptureSession session) {
                            throw new RuntimeException("Camera session configuration failed.");
                        }
                    },
                    backgroundHandler
            );
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }

    private void startBackgroundThread() {
        backgroundThread = new HandlerThread("CameraBackground");
        backgroundThread.start();
        backgroundHandler = new Handler(backgroundThread.getLooper());
    }

    private void stopBackgroundThread() {
        backgroundThread.quitSafely();
        try {
            backgroundThread.join();
            backgroundThread = null;
            backgroundHandler = null;
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    // Convert YUV_420_888 to RGB
    private int[][][] yuv420ToRgb(Image image) {
        int w = image.getWidth();
        int h = image.getHeight();
        int[][][] rgb = new int[h][w][3];

        ByteBuffer yBuffer = image.getPlanes()[0].getBuffer();
        ByteBuffer uBuffer = image.getPlanes()[1].getBuffer();
        ByteBuffer vBuffer = image.getPlanes()[2].getBuffer();

        int yRowStride = image.getPlanes()[0].getRowStride();
        int uvRowStride = image.getPlanes()[1].getRowStride();
        int uvPixelStride = image.getPlanes()[1].getPixelStride();

        byte[] yBytes = new byte[yBuffer.remaining()];
        yBuffer.get(yBytes);
        byte[] uBytes = new byte[uBuffer.remaining()];
        uBuffer.get(uBytes);
        byte[] vBytes = new byte[vBuffer.remaining()];
        vBuffer.get(vBytes);

        for (int row = 0; row < h; row++) {
            for (int col = 0; col < w; col++) {
                int yIndex = row * yRowStride + col;
                int uvRow = row / 2;
                int uvCol = col / 2;
                int uvIndex = uvRow * uvRowStride + uvCol * uvPixelStride;

                int y = yBytes[yIndex] & 0xFF;
                int u = uBytes[uvIndex] & 0xFF;
                int v = vBytes[uvIndex] & 0xFF;

                // YUV to RGB conversion
                int r = (int) (y + 1.370705 * (v - 128));
                int g = (int) (y - 0.337633 * (u - 128) - 0.698001 * (v - 128));
                int b = (int) (y + 1.732446 * (u - 128));

                rgb[row][col][0] = clamp(r);
                rgb[row][col][1] = clamp(g);
                rgb[row][col][2] = clamp(b);
            }
        }

        return rgb;
    }

    private int clamp(int val) {
        return Math.max(0, Math.min(val, 255));
    }
}
