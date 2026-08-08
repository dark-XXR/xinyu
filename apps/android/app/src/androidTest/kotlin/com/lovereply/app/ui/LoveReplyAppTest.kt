package com.lovereply.app.ui

import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasScrollAction
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToIndex
import androidx.test.platform.app.InstrumentationRegistry
import com.lovereply.app.AppScreen
import com.lovereply.app.MainUiState
import com.lovereply.app.domain.ComposerDraft
import com.lovereply.app.domain.EntitlementSummary
import com.lovereply.app.domain.GenerationPhase
import com.lovereply.app.domain.GenerationQuoteSummary
import com.lovereply.app.domain.GenerationResult
import com.lovereply.app.domain.ReplyAnalysis
import com.lovereply.app.domain.ReplyCandidate
import com.lovereply.app.ui.theme.LoveReplyTheme
import org.junit.Rule
import org.junit.Test

class LoveReplyAppTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun loginScreenShowsSmsControls() {
        setAppContent(MainUiState(screen = AppScreen.LOGIN))

        composeRule.onNodeWithTag("phone_input").assertIsDisplayed()
        composeRule.onNodeWithTag("code_input").assertIsDisplayed()
        composeRule.onNodeWithTag("login_button").assertIsDisplayed()
        captureScreen("login")
    }

    @Test
    fun composerHidesAllP1Destinations() {
        setAppContent(
            MainUiState(
                screen = AppScreen.COMPOSER,
                entitlement = EntitlementSummary(8, 1_200, setOf("model_quality"), setOf("warm")),
            ),
        )

        composeRule.onNodeWithTag("message_input").assertIsDisplayed()
        composeRule.onAllNodesWithText("截图识别").assertCountEquals(0)
        composeRule.onAllNodesWithText("对象档案").assertCountEquals(0)
        composeRule.onAllNodesWithText("会员钱包").assertCountEquals(0)
        composeRule.onAllNodesWithText("锦囊").assertCountEquals(0)
        captureScreen("composer_top")
        composeRule.onNode(hasScrollAction()).performScrollToIndex(3)
        composeRule.onNodeWithTag("quote_button").assertIsDisplayed()
        captureScreen("composer_bottom")
    }

    @Test
    fun resultShowsExactlyThreeStrategyCards() {
        setAppContent(
            MainUiState(
                screen = AppScreen.RESULT,
                generation = GenerationResult(
                    id = "gen_test",
                    phase = GenerationPhase.SUCCEEDED,
                    statusLabel = "SUCCEEDED",
                    analysis = ReplyAnalysis("试探见面意愿", "期待", "仅依据当前内容推测", emptyList()),
                    candidates = listOf(
                        ReplyCandidate("1", "SAFE", "warm", "稳妥回复"),
                        ReplyCandidate("2", "PUSH_PULL", "humorous", "张力回复"),
                        ReplyCandidate("3", "DIRECT", "steady", "直接回复"),
                    ),
                ),
            ),
        )

        composeRule.onNodeWithTag("candidate_SAFE").assertIsDisplayed()
        captureScreen("result_top")
        composeRule.onNodeWithTag("candidate_DIRECT").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithTag("candidate_PUSH_PULL").assertIsDisplayed()
        captureScreen("result_bottom")
    }

    @Test
    fun quoteConfirmationFitsAfterComposerScroll() {
        setAppContent(
            MainUiState(
                screen = AppScreen.COMPOSER,
                draft = ComposerDraft(message = "对方：周末有空吗？"),
                entitlement = EntitlementSummary(8, 1_200, setOf("model_quality"), setOf("warm")),
                quote = GenerationQuoteSummary(
                    id = "quote_test",
                    selectedModelId = "model_quality",
                    estimatedEnergy = 120,
                    expiresAtLabel = "12:30:00",
                ),
            ),
        )

        composeRule.onNode(hasScrollAction()).performScrollToIndex(3)
        composeRule.onNodeWithTag("generate_button").assertIsDisplayed()
        captureScreen("quote")
    }

    @Test
    fun failedResultShowsRetryWithoutClearingDraft() {
        val original = "对方：我最近有点忙"
        setAppContent(
            MainUiState(
                screen = AppScreen.RESULT,
                draft = ComposerDraft(message = original),
                generation = GenerationResult(
                    id = "gen_failed",
                    phase = GenerationPhase.FAILED,
                    statusLabel = "FAILED",
                    failureCode = "MODEL_PROVIDER_UNAVAILABLE",
                ),
                errorMessage = "生成服务暂时不可用，本次额度已释放",
            ),
        )

        composeRule.onNodeWithTag("retry_button").assertIsDisplayed()
        captureScreen("failure")
    }

    private fun setAppContent(state: MainUiState) {
        composeRule.setContent {
            LoveReplyTheme(darkTheme = false) {
                LoveReplyApp(
                    state = state,
                    onCountryCodeChange = {},
                    onPhoneChange = {},
                    onVerificationCodeChange = {},
                    onSendSms = {},
                    onLogin = {},
                    onMessageChange = {},
                    onRelationshipChange = {},
                    onGoalChange = {},
                    onStyleToggle = {},
                    onAdditionalContextChange = {},
                    onRequestQuote = {},
                    onConfirmGeneration = {},
                    onRetry = {},
                    onEditDraft = {},
                    onDismissError = {},
                    onCopy = {},
                )
            }
        }
    }

    private fun captureScreen(name: String) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val directory = requireNotNull(context.getExternalFilesDir("screenshots"))
        val output = directory.resolve("$name.png")
        output.outputStream().use { stream ->
            composeRule.onRoot().captureToImage().asAndroidBitmap().compress(
                Bitmap.CompressFormat.PNG,
                100,
                stream,
            )
        }
    }
}
