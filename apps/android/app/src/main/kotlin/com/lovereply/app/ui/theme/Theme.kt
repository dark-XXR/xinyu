package com.lovereply.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF146B62),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD2EEE8),
    onPrimaryContainer = Color(0xFF0A3732),
    secondary = Color(0xFFB64D3B),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFFFDAD3),
    onSecondaryContainer = Color(0xFF4B160D),
    background = Color(0xFFF7F8F6),
    onBackground = Color(0xFF1A1C1B),
    surface = Color(0xFFF7F8F6),
    onSurface = Color(0xFF1A1C1B),
    surfaceVariant = Color(0xFFE4E8E5),
    onSurfaceVariant = Color(0xFF444846),
    outline = Color(0xFF747976),
    error = Color(0xFFBA1A1A),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF9AD1C8),
    onPrimary = Color(0xFF003730),
    primaryContainer = Color(0xFF005047),
    onPrimaryContainer = Color(0xFFD2EEE8),
    secondary = Color(0xFFFFB4A6),
    onSecondary = Color(0xFF6E2519),
    background = Color(0xFF111413),
    onBackground = Color(0xFFE1E3E1),
    surface = Color(0xFF111413),
    onSurface = Color(0xFFE1E3E1),
    surfaceVariant = Color(0xFF404846),
    onSurfaceVariant = Color(0xFFC0C9C6),
)

@Composable
fun LoveReplyTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}
