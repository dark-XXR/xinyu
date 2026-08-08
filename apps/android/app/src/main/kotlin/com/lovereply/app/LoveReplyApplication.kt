package com.lovereply.app

import android.app.Application
import com.lovereply.app.data.DeviceIdStore
import com.lovereply.app.data.LoveReplyRepository
import com.lovereply.app.data.NetworkLoveReplyRepository
import com.lovereply.app.data.SessionStore

class LoveReplyApplication : Application() {
    lateinit var repository: LoveReplyRepository
        private set

    override fun onCreate() {
        super.onCreate()
        repository = NetworkLoveReplyRepository(
            baseUrl = BuildConfig.API_BASE_URL,
            sessionStore = SessionStore(this),
            deviceIdStore = DeviceIdStore(this),
        )
    }
}
