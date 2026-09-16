plugins {
    id("com.android.application")
}

val egmApiBaseUrl = providers.gradleProperty("EGM_API_BASE_URL").orElse("").get()
val escapedApiBaseUrl = egmApiBaseUrl.replace("\\", "\\\\").replace("\"", "\\\"")

android {
    namespace = "com.smartpickshop.egm4000"
    compileSdk = 36

    buildFeatures {
        buildConfig = true
    }

    defaultConfig {
        applicationId = "com.smartpickshop.egm4000"
        minSdk = 26
        targetSdk = 36
        versionCode = 4
        versionName = "0.3.0-production-ready"
        buildConfigField("String", "EGM_API_BASE_URL", "\"$escapedApiBaseUrl\"")
    }
}
