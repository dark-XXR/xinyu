package com.lovereply.app

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.lovereply.app.ui.LoveReplyApp
import com.lovereply.app.ui.theme.LoveReplyTheme

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels {
        MainViewModel.factory((application as LoveReplyApplication).repository)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val state by viewModel.state.collectAsStateWithLifecycle()
            LoveReplyTheme {
                LoveReplyApp(
                    state = state,
                    onCountryCodeChange = viewModel::updateCountryCode,
                    onPhoneChange = viewModel::updatePhone,
                    onVerificationCodeChange = viewModel::updateVerificationCode,
                    onSendSms = viewModel::sendSms,
                    onLogin = viewModel::login,
                    onMessageChange = viewModel::updateMessage,
                    onRelationshipChange = viewModel::updateRelationshipStage,
                    onGoalChange = viewModel::updateCommunicationGoal,
                    onStyleToggle = viewModel::toggleStyle,
                    onAdditionalContextChange = viewModel::updateAdditionalContext,
                    onRequestQuote = viewModel::requestQuote,
                    onConfirmGeneration = viewModel::confirmGeneration,
                    onRetry = viewModel::retryGeneration,
                    onEditDraft = viewModel::editDraft,
                    onDismissError = viewModel::clearError,
                    onCopy = ::copyReply,
                )
            }
        }
    }

    private fun copyReply(text: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("回复", text))
    }
}
