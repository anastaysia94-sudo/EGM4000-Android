package com.smartpickshop.egm4000;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public final class ApiClient {
    private final String baseUrl;

    public ApiClient(String baseUrl) {
        String value = baseUrl == null ? "" : baseUrl.trim();
        while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
        if (!value.startsWith("https://")) throw new IllegalArgumentException("EGM4000 server URL must use HTTPS.");
        this.baseUrl = value;
    }

    public JSONObject get(String path, String bearerToken) throws Exception {
        return request("GET", path, null, bearerToken);
    }

    public JSONObject post(String path, JSONObject body, String bearerToken) throws Exception {
        return request("POST", path, body == null ? new JSONObject() : body, bearerToken);
    }

    private JSONObject request(String method, String path, JSONObject body, String bearerToken) throws Exception {
        URL url = new URL(baseUrl + (path.startsWith("/") ? path : "/" + path));
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod(method);
        conn.setConnectTimeout(12000);
        conn.setReadTimeout(20000);
        conn.setRequestProperty("Accept", "application/json");
        conn.setRequestProperty("User-Agent", "EGM4000-Android/0.2");
        if (bearerToken != null && !bearerToken.isEmpty()) conn.setRequestProperty("Authorization", "Bearer " + bearerToken);
        if (body != null) {
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
            conn.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream os = conn.getOutputStream()) { os.write(bytes); }
        }
        int code = conn.getResponseCode();
        InputStream stream = code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream();
        String text = read(stream);
        conn.disconnect();
        JSONObject json = text == null || text.trim().isEmpty() ? new JSONObject() : new JSONObject(text);
        if (code < 200 || code >= 300) throw new ApiException(code, json.optString("error", "HTTP " + code), json);
        return json;
    }

    private static String read(InputStream stream) throws Exception {
        if (stream == null) return "";
        StringBuilder b = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) b.append(line);
        }
        return b.toString();
    }

    public static final class ApiException extends Exception {
        public final int statusCode;
        public final JSONObject payload;
        public ApiException(int statusCode, String message, JSONObject payload) {
            super(message);
            this.statusCode = statusCode;
            this.payload = payload;
        }
    }
}
