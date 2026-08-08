package com.lovereply.app.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

data class SessionTokens(
    val accessToken: String,
    val refreshToken: String,
)

class SessionStore(context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val preferences = EncryptedSharedPreferences.create(
        context,
        "secure_session",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    fun read(): SessionTokens? {
        val accessToken = preferences.getString(KEY_ACCESS_TOKEN, null) ?: return null
        val refreshToken = preferences.getString(KEY_REFRESH_TOKEN, null) ?: return null
        return SessionTokens(accessToken, refreshToken)
    }

    fun write(tokens: SessionTokens) {
        preferences.edit()
            .putString(KEY_ACCESS_TOKEN, tokens.accessToken)
            .putString(KEY_REFRESH_TOKEN, tokens.refreshToken)
            .apply()
    }

    fun clear() {
        preferences.edit().clear().apply()
    }

    private companion object {
        const val KEY_ACCESS_TOKEN = "access_token"
        const val KEY_REFRESH_TOKEN = "refresh_token"
    }
}
class DeviceIdStore(context: Context) {
    private val preferences = context.getSharedPreferences("installation", Context.MODE_PRIVATE)

    val value: String
        get() = preferences.getString(KEY_DEVICE_ID, null)
            ?: "android-${java.util.UUID.randomUUID()}".also {
                preferences.edit().putString(KEY_DEVICE_ID, it).apply()
            }

    private companion object {
        const val KEY_DEVICE_ID = "device_id"
    }
}
