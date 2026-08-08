package com.lovereply.app.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import com.lovereply.app.AppScreen
import com.lovereply.app.MainUiState
import com.lovereply.app.domain.EntitlementSummary
import com.lovereply.app.domain.GenerationPhase
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
        composeRule.onNodeWithTag("candidate_PUSH_PULL").assertIsDisplayed()
        composeRule.onNodeWithTag("candidate_DIRECT").assertIsDisplayed()
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
}
