/*
 * Custom Mixer for Twin-Engine Flying Wing UAV
 * 
 * This mixer provides:
 * - Independent throttle control for left/right motors
 * - Differential thrust for yaw control
 * - Elevon mixing for pitch and roll
 */

#include "platform.h"
#include "flight/mixer.h"

#ifdef USE_MIXER_CUSTOM_TWIN

// Mixer rules for twin-engine flying wing
// Format: {type, output_index, input, rate, offset}
static const mixerRule_t mixerRulesTwinEngine[] = {
    // ===== MOTORS =====
    
    // Motor 1 (Left): Throttle + Yaw differential
    // When yaw stick right → reduce left motor
    { MIXER_MOTOR,  0, INPUT_STABILIZED_THROTTLE, 1000, 0 },
    { MIXER_MOTOR,  0, INPUT_STABILIZED_YAW,      -500, 0 },  // Negative = reduce on right yaw
    
    // Motor 2 (Right): Throttle - Yaw differential  
    // When yaw stick right → increase right motor
    { MIXER_MOTOR,  1, INPUT_STABILIZED_THROTTLE, 1000, 0 },
    { MIXER_MOTOR,  1, INPUT_STABILIZED_YAW,       500, 0 },  // Positive = increase on right yaw
    
    // ===== SERVOS (Elevons) =====
    
    // Servo 1 (Left Elevon): Pitch + Roll
    // Pitch up → both elevons up
    // Roll right → left elevon up
    { MIXER_SERVO,  0, INPUT_STABILIZED_PITCH,     500, 0 },
    { MIXER_SERVO,  0, INPUT_STABILIZED_ROLL,     -500, 0 },
    
    // Servo 2 (Right Elevon): Pitch - Roll
    // Pitch up → both elevons up
    // Roll right → right elevon down
    { MIXER_SERVO,  1, INPUT_STABILIZED_PITCH,     500, 0 },
    { MIXER_SERVO,  1, INPUT_STABILIZED_ROLL,      500, 0 },
};

// Mixer definition
const mixer_t mixerTwinEngine = {
    .motorCount = 2,  // 2 motors
    .servoCount = 2,  // 2 servos (elevons)
    .rules = mixerRulesTwinEngine,
    .ruleCount = sizeof(mixerRulesTwinEngine) / sizeof(mixerRule_t),
};

#endif // USE_MIXER_CUSTOM_TWIN

/*
 * Usage in CLI:
 * 
 * mixer CUSTOM
 * mmix reset
 * mmix 0 1.0 0.0 0.0 -0.5   # Motor 1 (Left)
 * mmix 1 1.0 0.0 0.0  0.5   # Motor 2 (Right)
 * 
 * smix reset
 * smix 0 3 0 50 0 -100 100  # Elevon Left (Pitch)
 * smix 1 3 1 -50 0 -100 100 # Elevon Left (Roll)
 * smix 2 4 0 50 0 -100 100  # Elevon Right (Pitch)
 * smix 3 4 1 50 0 -100 100  # Elevon Right (Roll)
 * 
 * save
 */
