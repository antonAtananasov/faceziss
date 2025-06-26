package utils.java;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import android.content.Context;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraDevice.StateCallback;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CaptureRequest;
import android.graphics.ImageFormat;
import android.media.ImageReader;
import android.view.Surface;
import android.media.Image;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

class CameraChecker {
    Context context;
    CameraManager cameraManager;
    CameraDevice cameraDevice;
    Handler handler;
    int width = 320;
    int height = 240;
    int[][][] rgbArray;

    public CameraChecker(Context context) {
        this.context = context;
        this.cameraManager = (CameraManager) context.getSystemService(context.CAMERA_SERVICE);
        this.handler = new Handler(Looper.getMainLooper());
    }

    public String[] getCameraIdList() throws CameraAccessException {
        return this.cameraManager.getCameraIdList();
    }

    public CameraCharacteristics getCameraCharacteristics(String cameraId) throws CameraAccessException {
        return this.cameraManager.getCameraCharacteristics(cameraId);
    }

    public String[][] getSimultaneousCameraCombinationIds() throws CameraAccessException {
        String[] cameraIds = this.getCameraIdList();
        List<String[]> combinationsList = new ArrayList<String[]>();
        for (String cameraId : cameraIds) {
            List<String> combinations = new ArrayList<String>();
            CameraCharacteristics characteristics = this.getCameraCharacteristics(cameraId);
            int simultaneousCombinationsFlags = characteristics.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA;
            char[] charFlags = Integer.toString(simultaneousCombinationsFlags).toCharArray();
            for (int i = 0; i < charFlags.length; i++) {
                if (charFlags[i] == '1')
                    combinations.add(cameraIds[i]);
            }
            if (combinations.size() > 0) {

                String[] combinationResult = combinations.toArray(new String[combinations.size()]);
                boolean matches = true;
                for (String[] recordedCombination : combinationsList) {
                    for (int i = 0; i < combinationResult.length; i++)
                        if (recordedCombination[i] != combinationResult[i])
                            matches = false;
                }
                if (!matches)
                    combinationsList.add(combinationResult);
            }
        }
        return combinationsList.toArray(new String[combinationsList.size()][]);
    }

    public CameraDevice openCamera(String cameraId) throws CameraAccessException {

        StateCallback stateCallback = new CameraDevice.StateCallback() {
            @Override
            public void onOpened(CameraDevice camera) {
                cameraDevice = camera;
                Log.i("python", "Camera " + cameraId + " opened");
            }

            @Override
            public void onDisconnected(CameraDevice camera) {
                camera.close();
                Log.i("python", "Camera " + cameraId + " closed");
            }

            @Override
            public void onError(CameraDevice camera, int error) {
                camera.close();
                Log.i("python", "Camera " + cameraId + " error");
            }
        };

        this.cameraManager.openCamera(cameraId, stateCallback, this.handler);
        return this.cameraDevice;
    }

    public int[][][] getLatestImage(CameraDevice cameraDevice) throws CameraAccessException {
        ImageReader imageReader = ImageReader.newInstance(this.width, this.height, ImageFormat.YUV_420_888, 2);
        ImageReader.OnImageAvailableListener listener = new ImageReader.OnImageAvailableListener() {
            @Override
            public void onImageAvailable(ImageReader reader) {
                Image yuv420image = reader.acquireLatestImage();
                if (yuv420image != null) {
                    rgbArray = convertYUV420ToRGB(yuv420image);
                    yuv420image.close();
                    // Use rgbArray...
                }
            }
        };
        imageReader.setOnImageAvailableListener(listener, this.handler);

        Surface surface = imageReader.getSurface();

        CaptureRequest.Builder builder = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
        builder.addTarget(surface);

        Handler handler = this.handler;

        CameraCaptureSession.StateCallback captureSessionStateCallback = new CameraCaptureSession.StateCallback() {
            @Override
            public void onConfigured(CameraCaptureSession session) {
                try {
                    session.setRepeatingRequest(builder.build(), null, handler);
                } catch (CameraAccessException e) {
                    e.printStackTrace();
                }
            }

            @Override
            public void onConfigureFailed(CameraCaptureSession session) {
                Log.i("python", "Camera Configuration failed");
            }
        };

        cameraDevice.createCaptureSession(
                Collections.singletonList(surface),
                captureSessionStateCallback,
                this.handler);

        return rgbArray;
    }

    public void closeCamera(CameraDevice cameraDevice) throws CameraAccessException {
        cameraDevice.close();
    }

    private int[][][] convertYUV420ToRGB(Image image) {
        int width = image.getWidth();
        int height = image.getHeight();
        int[][][] rgb = new int[height][width][3]; // [row][col][channel]

        Image.Plane[] planes = image.getPlanes();
        ByteBuffer yBuffer = planes[0].getBuffer();
        ByteBuffer uBuffer = planes[1].getBuffer();
        ByteBuffer vBuffer = planes[2].getBuffer();

        int yRowStride = planes[0].getRowStride();
        int uvRowStride = planes[1].getRowStride();
        int uvPixelStride = planes[1].getPixelStride();

        byte[] yBytes = new byte[yBuffer.remaining()];
        byte[] uBytes = new byte[uBuffer.remaining()];
        byte[] vBytes = new byte[vBuffer.remaining()];

        yBuffer.get(yBytes);
        uBuffer.get(uBytes);
        vBuffer.get(vBytes);

        for (int j = 0; j < height; j++) {
            for (int i = 0; i < width; i++) {
                int yIndex = j * yRowStride + i;
                int uvIndex = (j / 2) * uvRowStride + (i / 2) * uvPixelStride;

                int y = yBytes[yIndex] & 0xFF;
                int u = uBytes[uvIndex] & 0xFF;
                int v = vBytes[uvIndex] & 0xFF;

                // YUV to RGB conversion
                int r = (int) (y + 1.370705 * (v - 128));
                int g = (int) (y - 0.337633 * (u - 128) - 0.698001 * (v - 128));
                int b = (int) (y + 1.732446 * (u - 128));

                // Clamp to [0, 255]
                r = Math.max(0, Math.min(255, r));
                g = Math.max(0, Math.min(255, g));
                b = Math.max(0, Math.min(255, b));

                // Store in [height][width][RGB]
                rgb[j][i][0] = r;
                rgb[j][i][1] = g;
                rgb[j][i][2] = b;
            }
        }

        return rgb;
    }

}