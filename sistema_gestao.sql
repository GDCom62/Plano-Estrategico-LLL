```sql
CREATE DATABASE sistema_gestao;
USE sistema_gestao;

CREATE TABLE Usuarios (
    id_usuario INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(100) NOT NULL
);

CREATE TABLE Acoes (
    id_acao INT PRIMARY KEY AUTO_INCREMENT,
    id_responsavel INT,
    descricao_acao VARCHAR(255) NOT NULL,
    prazo DATE,
    status ENUM('Pendente', 'Executando', 'Concluido', 'Atrasado') DEFAULT 'Pendente',
    FOREIGN KEY (id_responsavel) REFERENCES Usuarios(id_usuario)
);

CREATE TABLE Historico_Acoes (
    id_log INT PRIMARY KEY AUTO_INCREMENT,
    id_acao INT,
    data_alteracao DATETIME DEFAULT CURRENT_TIMESTAMP,
    valor_antigo VARCHAR(50),
    valor_novo VARCHAR(50),
    FOREIGN KEY (id_acao) REFERENCES Acoes(id_acao)
);

-- Dados iniciais para teste
INSERT INTO Usuarios (nome) VALUES ('João Silva'), ('Maria Souza'), ('Carlos Oliveira');

```

---