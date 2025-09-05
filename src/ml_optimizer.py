#!/usr/bin/env python3
"""
Machine Learning-based CBS Parameter Optimizer
Uses reinforcement learning and neural networks to optimize CBS parameters
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, List, Tuple, Optional, Any
import json
import logging
from pathlib import Path
import pickle
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CBSNeuralNetwork(nn.Module):
    """Deep Neural Network for CBS parameter prediction"""
    
    def __init__(self, input_dim: int, hidden_dims: List[int], output_dim: int):
        super(CBSNeuralNetwork, self).__init__()
        
        layers = []
        prev_dim = input_dim
        
        # Hidden layers with batch normalization and dropout
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_dim = hidden_dim
        
        # Output layer
        layers.append(nn.Linear(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


class ReinforcementLearningAgent:
    """RL Agent for CBS parameter optimization using Deep Q-Learning"""
    
    def __init__(self, state_dim: int, action_dim: int, learning_rate: float = 0.001):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        
        # Q-network and target network
        self.q_network = CBSNeuralNetwork(state_dim, [256, 128, 64], action_dim)
        self.target_network = CBSNeuralNetwork(state_dim, [256, 128, 64], action_dim)
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        self.memory = []
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.gamma = 0.95  # Discount factor
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
        if len(self.memory) > 10000:
            self.memory.pop(0)
    
    def act(self, state):
        """Choose action using epsilon-greedy policy"""
        if np.random.random() < self.epsilon:
            return np.random.randint(self.action_dim)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        q_values = self.q_network(state_tensor)
        return q_values.argmax().item()
    
    def replay(self, batch_size: int = 32):
        """Train the Q-network using experience replay"""
        if len(self.memory) < batch_size:
            return
        
        batch = np.random.choice(len(self.memory), batch_size, replace=False)
        states = torch.FloatTensor([self.memory[i][0] for i in batch])
        actions = torch.LongTensor([self.memory[i][1] for i in batch])
        rewards = torch.FloatTensor([self.memory[i][2] for i in batch])
        next_states = torch.FloatTensor([self.memory[i][3] for i in batch])
        dones = torch.FloatTensor([self.memory[i][4] for i in batch])
        
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        next_q_values = self.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (self.gamma * next_q_values * (1 - dones))
        
        loss = nn.MSELoss()(current_q_values.squeeze(), target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def update_target_network(self):
        """Update target network with Q-network weights"""
        self.target_network.load_state_dict(self.q_network.state_dict())


class CBSParameterOptimizer:
    """Main optimizer class combining multiple ML techniques"""
    
    def __init__(self):
        self.rf_model = None
        self.gb_model = None
        self.nn_model = None
        self.rl_agent = None
        self.scaler = StandardScaler()
        self.feature_importance = {}
        self.optimization_history = []
    
    def prepare_features(self, traffic_data: Dict) -> np.ndarray:
        """Extract features from traffic data"""
        features = []
        
        # Traffic characteristics
        features.append(traffic_data.get('bitrate_mbps', 0))
        features.append(traffic_data.get('priority', 0))
        features.append(traffic_data.get('frame_size', 1500))
        features.append(traffic_data.get('burst_size', 1))
        features.append(traffic_data.get('fps', 30))
        
        # Network conditions
        features.append(traffic_data.get('background_load_mbps', 0))
        features.append(traffic_data.get('num_competing_streams', 0))
        features.append(traffic_data.get('link_utilization', 0))
        
        # QoS requirements
        features.append(traffic_data.get('max_latency_ms', 10))
        features.append(traffic_data.get('max_jitter_ms', 2))
        features.append(traffic_data.get('max_loss_rate', 0.001))
        
        return np.array(features)
    
    def train_models(self, training_data: pd.DataFrame):
        """Train all ML models"""
        
        # Prepare data
        feature_columns = [col for col in training_data.columns 
                          if col not in ['idle_slope', 'send_slope', 'hi_credit', 'lo_credit', 'performance_score']]
        
        X = training_data[feature_columns].values
        y = training_data[['idle_slope', 'send_slope', 'hi_credit', 'lo_credit']].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # Train Random Forest
        logger.info("Training Random Forest model...")
        self.rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        self.rf_model.fit(X_train, y_train)
        
        # Feature importance
        for i, col in enumerate(feature_columns):
            self.feature_importance[col] = self.rf_model.feature_importances_[i]
        
        # Train Gradient Boosting
        logger.info("Training Gradient Boosting model...")
        self.gb_model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        # GB expects single output, so train separate models
        self.gb_models = []
        for i in range(y.shape[1]):
            gb = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            gb.fit(X_train, y_train[:, i])
            self.gb_models.append(gb)
        
        # Train Neural Network
        logger.info("Training Neural Network model...")
        self.train_neural_network(X_train, y_train, X_test, y_test)
        
        # Evaluate models
        self.evaluate_models(X_test, y_test)
    
    def train_neural_network(self, X_train, y_train, X_test, y_test, epochs=100):
        """Train neural network model"""
        
        input_dim = X_train.shape[1]
        output_dim = y_train.shape[1]
        
        self.nn_model = CBSNeuralNetwork(input_dim, [128, 64, 32], output_dim)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.nn_model.parameters(), lr=0.001)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train)
        y_train_tensor = torch.FloatTensor(y_train)
        X_test_tensor = torch.FloatTensor(X_test)
        y_test_tensor = torch.FloatTensor(y_test)
        
        # Training loop
        best_loss = float('inf')
        patience = 10
        patience_counter = 0
        
        for epoch in range(epochs):
            # Training
            self.nn_model.train()
            optimizer.zero_grad()
            outputs = self.nn_model(X_train_tensor)
            loss = criterion(outputs, y_train_tensor)
            loss.backward()
            optimizer.step()
            
            # Validation
            self.nn_model.eval()
            with torch.no_grad():
                val_outputs = self.nn_model(X_test_tensor)
                val_loss = criterion(val_outputs, y_test_tensor)
            
            # Early stopping
            if val_loss < best_loss:
                best_loss = val_loss
                patience_counter = 0
                # Save best model
                self.best_nn_state = self.nn_model.state_dict()
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    break
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Train Loss = {loss:.4f}, Val Loss = {val_loss:.4f}")
        
        # Load best model
        self.nn_model.load_state_dict(self.best_nn_state)
    
    def evaluate_models(self, X_test, y_test):
        """Evaluate all models"""
        
        # Random Forest evaluation
        rf_pred = self.rf_model.predict(X_test)
        rf_mse = mean_squared_error(y_test, rf_pred)
        rf_r2 = r2_score(y_test, rf_pred)
        
        logger.info(f"Random Forest - MSE: {rf_mse:.4f}, R2: {rf_r2:.4f}")
        
        # Gradient Boosting evaluation
        gb_pred = np.column_stack([model.predict(X_test) for model in self.gb_models])
        gb_mse = mean_squared_error(y_test, gb_pred)
        gb_r2 = r2_score(y_test, gb_pred)
        
        logger.info(f"Gradient Boosting - MSE: {gb_mse:.4f}, R2: {gb_r2:.4f}")
        
        # Neural Network evaluation
        self.nn_model.eval()
        with torch.no_grad():
            X_test_tensor = torch.FloatTensor(X_test)
            nn_pred = self.nn_model(X_test_tensor).numpy()
        
        nn_mse = mean_squared_error(y_test, nn_pred)
        nn_r2 = r2_score(y_test, nn_pred)
        
        logger.info(f"Neural Network - MSE: {nn_mse:.4f}, R2: {nn_r2:.4f}")
    
    def optimize_parameters(self, traffic_data: Dict, method: str = 'ensemble') -> Dict:
        """Optimize CBS parameters for given traffic"""
        
        features = self.prepare_features(traffic_data)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        if method == 'rf':
            params = self.rf_model.predict(features_scaled)[0]
        elif method == 'gb':
            params = np.array([model.predict(features_scaled)[0] 
                              for model in self.gb_models])
        elif method == 'nn':
            self.nn_model.eval()
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features_scaled)
                params = self.nn_model(features_tensor).numpy()[0]
        elif method == 'ensemble':
            # Ensemble prediction
            rf_params = self.rf_model.predict(features_scaled)[0]
            gb_params = np.array([model.predict(features_scaled)[0] 
                                 for model in self.gb_models])
            
            self.nn_model.eval()
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features_scaled)
                nn_params = self.nn_model(features_tensor).numpy()[0]
            
            # Weighted average
            params = (rf_params * 0.4 + gb_params * 0.3 + nn_params * 0.3)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        result = {
            'idle_slope_mbps': params[0] / 1_000_000,
            'send_slope_mbps': params[1] / 1_000_000,
            'hi_credit_bits': params[2],
            'lo_credit_bits': params[3],
            'optimization_method': method,
            'traffic_characteristics': traffic_data
        }
        
        self.optimization_history.append(result)
        
        return result
    
    def adaptive_optimization(self, real_time_metrics: Dict) -> Dict:
        """Adaptive optimization based on real-time performance"""
        
        # Extract current performance
        current_latency = real_time_metrics.get('latency_ms', 0)
        current_jitter = real_time_metrics.get('jitter_ms', 0)
        current_loss = real_time_metrics.get('loss_rate', 0)
        
        # Calculate reward
        target_latency = real_time_metrics.get('target_latency_ms', 10)
        target_jitter = real_time_metrics.get('target_jitter_ms', 2)
        target_loss = real_time_metrics.get('target_loss_rate', 0.001)
        
        latency_penalty = max(0, current_latency - target_latency) / target_latency
        jitter_penalty = max(0, current_jitter - target_jitter) / target_jitter
        loss_penalty = max(0, current_loss - target_loss) / target_loss
        
        reward = 1.0 - (latency_penalty + jitter_penalty + loss_penalty) / 3
        
        # Update RL agent
        if self.rl_agent:
            state = self.prepare_features(real_time_metrics)
            action = self.rl_agent.act(state)
            
            # Apply action (adjust parameters)
            adjustments = self.decode_action(action)
            
            # Store experience for learning
            next_state = state  # Would be updated after applying adjustments
            done = reward > 0.95  # Consider done if performance is excellent
            
            self.rl_agent.remember(state, action, reward, next_state, done)
            self.rl_agent.replay()
            
            return adjustments
        
        return {}
    
    def decode_action(self, action: int) -> Dict:
        """Decode RL action to parameter adjustments"""
        
        # Define action space (simplified)
        actions = {
            0: {'idle_slope_delta': 0.1, 'hi_credit_delta': 100},
            1: {'idle_slope_delta': -0.1, 'hi_credit_delta': -100},
            2: {'idle_slope_delta': 0.05, 'lo_credit_delta': 50},
            3: {'idle_slope_delta': -0.05, 'lo_credit_delta': -50},
            # Add more actions as needed
        }
        
        return actions.get(action, {})
    
    def save_models(self, path: str = 'ml_models'):
        """Save trained models"""
        Path(path).mkdir(exist_ok=True)
        
        # Save Random Forest
        with open(f'{path}/rf_model.pkl', 'wb') as f:
            pickle.dump(self.rf_model, f)
        
        # Save Gradient Boosting
        with open(f'{path}/gb_models.pkl', 'wb') as f:
            pickle.dump(self.gb_models, f)
        
        # Save Neural Network
        torch.save(self.nn_model.state_dict(), f'{path}/nn_model.pth')
        
        # Save scaler
        with open(f'{path}/scaler.pkl', 'wb') as f:
            pickle.dump(self.scaler, f)
        
        # Save feature importance
        with open(f'{path}/feature_importance.json', 'w') as f:
            json.dump(self.feature_importance, f, indent=2)
        
        logger.info(f"Models saved to {path}")
    
    def load_models(self, path: str = 'ml_models'):
        """Load trained models"""
        
        # Load Random Forest
        with open(f'{path}/rf_model.pkl', 'rb') as f:
            self.rf_model = pickle.load(f)
        
        # Load Gradient Boosting
        with open(f'{path}/gb_models.pkl', 'rb') as f:
            self.gb_models = pickle.load(f)
        
        # Load Neural Network
        # Need to recreate architecture first
        self.nn_model = CBSNeuralNetwork(11, [128, 64, 32], 4)  # Adjust dimensions
        self.nn_model.load_state_dict(torch.load(f'{path}/nn_model.pth'))
        
        # Load scaler
        with open(f'{path}/scaler.pkl', 'rb') as f:
            self.scaler = pickle.load(f)
        
        # Load feature importance
        with open(f'{path}/feature_importance.json', 'r') as f:
            self.feature_importance = json.load(f)
        
        logger.info(f"Models loaded from {path}")


def generate_synthetic_training_data(n_samples: int = 10000) -> pd.DataFrame:
    """Generate synthetic training data for model training"""
    
    np.random.seed(42)
    data = []
    
    for _ in range(n_samples):
        # Generate random traffic characteristics
        bitrate_mbps = np.random.uniform(1, 100)
        priority = np.random.randint(0, 8)
        frame_size = np.random.choice([64, 256, 512, 1024, 1500, 9000])
        burst_size = np.random.randint(1, 20)
        fps = np.random.choice([10, 15, 24, 30, 60])
        
        # Network conditions
        background_load_mbps = np.random.uniform(0, 800)
        num_competing_streams = np.random.randint(0, 20)
        link_utilization = (bitrate_mbps + background_load_mbps) / 1000
        
        # QoS requirements
        max_latency_ms = np.random.uniform(1, 100)
        max_jitter_ms = np.random.uniform(0.1, 10)
        max_loss_rate = np.random.uniform(0.0001, 0.01)
        
        # Calculate "optimal" CBS parameters (simplified heuristic)
        idle_slope = bitrate_mbps * 1.25 * 1_000_000  # 25% headroom
        send_slope = idle_slope - 1_000_000_000  # 1 Gbps link
        hi_credit = frame_size * 8 * 1.5  # 1.5x frame size
        lo_credit = -frame_size * 8 * 2  # 2x frame size
        
        # Add some noise to make it more realistic
        idle_slope *= np.random.uniform(0.9, 1.1)
        hi_credit *= np.random.uniform(0.8, 1.2)
        lo_credit *= np.random.uniform(0.8, 1.2)
        
        # Calculate performance score (for evaluation)
        performance_score = np.random.uniform(0.7, 1.0)
        
        data.append({
            'bitrate_mbps': bitrate_mbps,
            'priority': priority,
            'frame_size': frame_size,
            'burst_size': burst_size,
            'fps': fps,
            'background_load_mbps': background_load_mbps,
            'num_competing_streams': num_competing_streams,
            'link_utilization': link_utilization,
            'max_latency_ms': max_latency_ms,
            'max_jitter_ms': max_jitter_ms,
            'max_loss_rate': max_loss_rate,
            'idle_slope': idle_slope,
            'send_slope': send_slope,
            'hi_credit': hi_credit,
            'lo_credit': lo_credit,
            'performance_score': performance_score
        })
    
    return pd.DataFrame(data)


def main():
    """Main function to demonstrate ML-based optimization"""
    
    # Generate training data
    logger.info("Generating synthetic training data...")
    training_data = generate_synthetic_training_data(10000)
    
    # Initialize optimizer
    optimizer = CBSParameterOptimizer()
    
    # Train models
    logger.info("Training ML models...")
    optimizer.train_models(training_data)
    
    # Save models
    optimizer.save_models()
    
    # Test optimization
    test_traffic = {
        'bitrate_mbps': 25,
        'priority': 6,
        'frame_size': 1500,
        'burst_size': 5,
        'fps': 30,
        'background_load_mbps': 400,
        'num_competing_streams': 8,
        'link_utilization': 0.425,
        'max_latency_ms': 10,
        'max_jitter_ms': 2,
        'max_loss_rate': 0.001
    }
    
    # Optimize using different methods
    for method in ['rf', 'gb', 'nn', 'ensemble']:
        result = optimizer.optimize_parameters(test_traffic, method=method)
        print(f"\n{method.upper()} Optimization:")
        print(f"  Idle Slope: {result['idle_slope_mbps']:.2f} Mbps")
        print(f"  Hi Credit: {result['hi_credit_bits']:.0f} bits")
        print(f"  Lo Credit: {result['lo_credit_bits']:.0f} bits")
    
    # Print feature importance
    print("\nTop 5 Important Features:")
    sorted_features = sorted(optimizer.feature_importance.items(), 
                           key=lambda x: x[1], reverse=True)[:5]
    for feature, importance in sorted_features:
        print(f"  {feature}: {importance:.3f}")


if __name__ == "__main__":
    main()