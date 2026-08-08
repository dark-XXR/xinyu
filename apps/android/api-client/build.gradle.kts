plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.love_reply.generated"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
    }

    sourceSets.named("main") {
        kotlin.srcDir("../../../packages/generated-api/kotlin/src/main/kotlin")
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions.jvmTarget = "17"
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.10.2")
    implementation("org.jetbrains.kotlin:kotlin-reflect:2.1.21")
    api("com.squareup.moshi:moshi-kotlin:1.15.2")
    api("com.squareup.moshi:moshi-adapters:1.15.2")
    api("com.squareup.okhttp3:logging-interceptor:5.1.0")
    api("com.squareup.retrofit2:retrofit:3.0.0")
    api("com.squareup.retrofit2:converter-moshi:3.0.0")
    api("com.squareup.retrofit2:converter-scalars:3.0.0")
}
