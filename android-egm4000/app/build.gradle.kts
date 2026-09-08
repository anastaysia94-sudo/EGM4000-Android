plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.egm4000.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.egm4000.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 12
        versionName = "0.12.0-sv09-full-intelligence"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures { compose = true }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2025.01.01"))
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    implementation("org.json:json:20250517")

    // Bundled Latin OCR works on-device immediately after install, avoiding a
    // first-use model download on slow/2G connections.
    implementation("com.google.mlkit:text-recognition:16.0.1")

    testImplementation("junit:junit:4.13.2")
}
