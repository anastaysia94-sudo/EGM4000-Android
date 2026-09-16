plugins {
    id("com.android.application")
}

val egmApiBaseUrl = providers.gradleProperty("EGM_API_BASE_URL").orElse("").get()
val escapedApiBaseUrl = egmApiBaseUrl.replace("\\", "\\\\").replace("\"", "\\\"")

val releaseStoreFile = providers.gradleProperty("EGM_SIGNING_STORE_FILE").orNull
val releaseStorePassword = providers.gradleProperty("EGM_SIGNING_STORE_PASSWORD").orNull
val releaseKeyAlias = providers.gradleProperty("EGM_SIGNING_KEY_ALIAS").orNull
val releaseKeyPassword = providers.gradleProperty("EGM_SIGNING_KEY_PASSWORD").orNull
val hasReleaseSigning = listOf(releaseStoreFile, releaseStorePassword, releaseKeyAlias, releaseKeyPassword).all { !it.isNullOrBlank() }

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

    signingConfigs {
        if (hasReleaseSigning) {
            create("production") {
                storeFile = file(releaseStoreFile!!)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
                enableV1Signing = true
                enableV2Signing = true
            }
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            if (hasReleaseSigning) {
                signingConfig = signingConfigs.getByName("production")
            }
        }
    }
}
