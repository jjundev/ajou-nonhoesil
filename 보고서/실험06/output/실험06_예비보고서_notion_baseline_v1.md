<table_of_contents color="gray"/>
<empty-block/>
# 실험 목적
1비트 상태를 저장하는 기억 소자인 래치와 플립플롭을 이해하고, 종류에 따라 달라지는 동작 특성을 확인하는 것이 이번 실험의 목적이다. 같은 기억 소자를 논리 게이트로 직접 구성해 보는 경우와 완성된 IC로 쓰는 경우를 모두 다룬다.
실험은 74HC00의 NAND 네 개로 Enable이 있는 SR Latch를 구성하는 데서 시작한다. Enable이 1일 때 S와 R에 따라 출력 Q가 Set·Reset되거나 앞 값을 유지하는지 보고, S=R=1에서 Q와 Q'가 함께 1이 되는 것도 확인한다. 이어 같은 회로의 R 입력 자리에 74HC04로 뒤집은 D를 넣어 D Latch로 바꾸고, Q가 D를 따라가는지 본다. 마지막으로 회로를 모두 걷고 JK 플립플롭 IC인 74HC76을 꽂아, 비동기 입력 SET·RESET의 동작과 CLK의 하강 에지마다 J·K에 따라 출력이 바뀌는 모습을 확인한다.
<empty-block/>
<empty-block/>
# 실험 이론
## 래치와 플립플롭
래치(Latch)와 플립플롭(Flip-Flop)은 1비트의 상태(Set 또는 Reset)를 저장하는 기억 소자다. 제어 입력에 따라 저장된 값을 그대로 유지하거나 새 입력을 받아 저장하고, 전원이 끊기면 저장한 정보가 사라지는 휘발성 소자다. 레지스터, CPU 캐시, 주기억장치 같은 저장 장치가 이런 소자로 구성된다.
두 소자는 새 입력을 받아들이는 시점에서 갈린다. 래치는 Enable 같은 제어 입력이 1인 동안 계속 입력을 반영하는 레벨 트리거(Level-triggered) 소자이고, 강의노트는 클럭 없이 동작한다는 뜻에서 비동기 기억소자로 분류한다. 플립플롭은 클럭이 바뀌는 순간, 곧 상승 에지나 하강 에지에서만 입력을 반영하는 에지 트리거(Edge-triggered) 소자이며 클럭에 맞춰 동작하는 동기 기억소자다.
진리표에서 Q(t)는 출력 Q의 지금 값이고 Q(t-1)은 바로 앞의 값이다. Q(t-1)은 앞 상태를 그대로 유지한다는 뜻이고, Q(t-1)'은 앞 상태를 뒤집는다는 뜻이다.
<empty-block/>
## SR 래치
이번 실험의 SR Latch는 NAND 게이트 네 개로 이루어진다. 앞단 NAND 두 개가 S와 R을 각각 Enable E와 묶고, 뒷단 NAND 두 개는 서로의 출력을 입력으로 되먹이는 교차 결합 구조로 Q와 Q'를 낸다.
- (S·E)', (E·R)' : 앞단 NAND의 출력
- Q = ((S·E)'·Q')'
- Q' = ((E·R)'·Q)'
E=0이면 앞단 NAND의 출력이 S·R과 관계없이 모두 1이다. 1은 NAND에서 결과를 바꾸지 않는 입력이므로 뒷단은 Q = (Q')', Q' = Q'가 되어 들어 있던 값을 그대로 유지한다. E=1이고 S=1, R=0이면 (S·E)'=0이 Q를 1로 올리고, 그 Q가 Q'를 0으로 내려 Set 상태가 된다. 반대로 S=0, R=1이면 Q'가 1, Q가 0인 Reset 상태가 되고, S=R=0이면 앞단 출력이 모두 1이라 E=0일 때처럼 앞 값을 유지한다.
S=R=1이면 앞단 두 출력이 모두 0이 되어 Q와 Q'가 함께 1이 된다. 두 출력이 서로 보수라는 전제가 깨지는 상태이고, 이 상태에서 S와 R을 동시에 0으로 내리면 어느 쪽으로 정착할지 정해지지 않는다. 그래서 강의노트는 이 입력을 부정(X) 상태로 두고 사용하지 않는다고 적는다. 이번 실험에서는 두 출력이 함께 1이 되는지만 확인한다.
교차 결합된 두 NAND는 전원을 넣은 직후 어느 값으로 시작할지 정해져 있지 않다. 강의노트가 첫 입력으로 Set 또는 Reset을 넣으라고 한 것은 되먹임 값 Q, Q'를 먼저 정해 두기 위해서다.
<empty-block/>
## D 래치
D Latch는 SR Latch의 S 자리에 D를, R 자리에 D를 인버터로 뒤집은 D'를 넣은 회로다.
- Q = ((D·E)'·Q')'
- Q' = ((E·D')'·Q)'
S와 R에 늘 서로 반대인 값이 들어가므로 S=R=1인 부정 상태가 구조적으로 생기지 않는다. E=1이면 D=1이 Set, D=0이 Reset이 되어 Q가 D를 그대로 따라가고, E=0이면 앞단 출력이 모두 1이 되어 마지막 D 값을 유지한다. 입력이 하나로 줄어든 대신 SR Latch의 S=R=0처럼 E=1인 채로 값을 유지하는 입력은 없어지고, 유지는 E=0일 때만 한다.
<empty-block/>
## JK 플립플롭과 74HC76
JK 플립플롭은 SR 플립플롭의 S·R 자리에 J·K를 두되, J=K=1일 때 앞 출력의 보수를 내도록 만들어 부정 상태를 없앤 것이다. 클럭 에지에서 J=0, K=0이면 유지, J=0, K=1이면 Reset, J=1, K=0이면 Set, J=K=1이면 토글이다. 에지에서의 동작을 식 하나로 쓰면 다음과 같다.
- Q(t) = J·Q(t-1)' + K'·Q(t-1)
74HC76은 이런 JK 플립플롭 두 개가 들어 있는 16핀 IC이고, 이번 실험에서는 그중 하나만 쓴다. 74HC76의 CLK는 1에서 0으로 떨어지는 하강 에지(Falling Edge)에서 동작한다. 클럭이 0에서 1로 오를 때는 출력이 바뀌지 않는다.
각 플립플롭에는 클럭과 관계없이 출력을 정하는 비동기 입력 SET과 RESET이 있다. 둘 다 0일 때 작동하는 Active Low 입력이라, SET=0이면 Q가 1로, RESET=0이면 Q가 0으로 곧바로 정해지고 J·K·CLK보다 먼저 반영된다. 따라서 J와 K에 따른 동작을 볼 때는 SET과 RESET을 모두 1로 둔다.
<empty-block/>
## 사용하는 게이트
SR Latch는 74HC00의 NAND만으로, D Latch는 여기에 74HC04의 NOT 하나를 더해 구성한다. 아래 표는 H를 1, L을 0으로 읽는 양논리로 적었고, X는 어느 값이든 상관없다는 뜻이다.
- **2입력 NAND** (Y = (A·B)')
	<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>X</td>
<td>1</td>
</tr>
<tr>
<td>X</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
	</table>
- **NOT** (Y = A')
	<table header-row="true">
<tr>
<td>A</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
</tr>
	</table>
<empty-block/>
<empty-block/>
# 실험 부품
## 준비물
<table header-row="true">
<tr>
<td>품목</td>
<td>규격</td>
<td>수량</td>
<td>비고</td>
</tr>
<tr>
<td>전압원</td>
<td>+5V</td>
<td>1</td>
<td>모든 IC의 전원 핀과 입력에 공급</td>
</tr>
<tr>
<td>오실로스코프</td>
<td></td>
<td></td>
<td>출력은 LED로 확인한다</td>
</tr>
<tr>
<td>74HC00</td>
<td>quad 2-input NAND, DIP-14</td>
<td>1</td>
<td>SR Latch, D Latch. NAND 네 개를 모두 쓴다</td>
</tr>
<tr>
<td>74HC04</td>
<td>hex inverter, DIP-14</td>
<td>1</td>
<td>D Latch에서 D를 뒤집는다. 인버터 하나만 쓴다</td>
</tr>
<tr>
<td>74HC10</td>
<td>triple 3-input NAND</td>
<td></td>
<td>이번 실험 항목에는 쓰지 않는다</td>
</tr>
<tr>
<td>74HC74</td>
<td>dual D-type flip-flop</td>
<td></td>
<td>이번 실험 항목에는 쓰지 않는다</td>
</tr>
<tr>
<td>74HC76</td>
<td>dual JK flip-flop, DIP-16</td>
<td>1</td>
<td>JK F/F. 플립플롭 하나만 쓴다</td>
</tr>
<tr>
<td>발광다이오드</td>
<td></td>
<td>4</td>
<td>출력 Q와 Q'에 하나씩 두 개를 쓴다</td>
</tr>
<tr>
<td>저항</td>
<td>330Ω</td>
<td>4</td>
<td>발광다이오드마다 하나씩 직렬로 넣는다</td>
</tr>
<tr>
<td>브레드보드</td>
<td></td>
<td>1</td>
<td>IC와 배선을 올린다</td>
</tr>
<tr>
<td>점퍼선</td>
<td></td>
<td>적당량</td>
<td>입력을 +5V·GND에 물리고 게이트 사이를 잇는다</td>
</tr>
</table>
<empty-block/>
## 핀 배치
<table header-row="true">
<tr>
<td>IC</td>
<td>입력</td>
<td>출력</td>
<td>VCC</td>
<td>GND</td>
</tr>
<tr>
<td>74HC00 (quad 2-input NAND)</td>
<td>1·2, 4·5, 9·10, 12·13</td>
<td>3, 6, 8, 11</td>
<td>14</td>
<td>7</td>
</tr>
<tr>
<td>74HC76 (dual JK F/F, 1번)</td>
<td>CLK=1, SET=2, RESET=3, J=4, K=16</td>
<td>Q=15, Q'=14</td>
<td>5</td>
<td>13</td>
</tr>
<tr>
<td>74HC76 (dual JK F/F, 2번)</td>
<td>CLK=6, SET=7, RESET=8, J=9, K=12</td>
<td>Q=11, Q'=10</td>
<td>5</td>
<td>13</td>
</tr>
</table>
74HC04는 인버터 6개짜리로 1→2, 3→4, 5→6, 9→8, 11→10, 13→12이고 VCC는 14번, GND는 7번이다.
강의노트 회로도에는 74HC00과 74HC04의 신호 핀 번호가, 74HC76 그림에는 전원을 포함한 16핀 전부가 적혀 있고 모두 데이터시트의 배치와 일치한다. 74HC00과 74HC04의 전원 핀은 회로도에 없어 데이터시트에서 확인했다. 74HC76은 전원이 칩 모서리가 아니라 5번(VCC)과 13번(GND)에 있어 14핀 칩이나 다른 16핀 칩과 자리가 다르다. K 입력도 J(4번)의 반대쪽 맨 위인 16번이다.
<empty-block/>
<empty-block/>
# 실험 과정 및 예상 결과
## 실험 1) SR Latch with Enable
74HC00의 1번과 2번에 S와 E를, 4번과 5번에 E와 R을 넣어 앞단 NAND 두 개를 만들고, 그 출력 3번과 6번을 뒷단 NAND의 9번과 13번으로 보낸다. 뒷단 출력 8번(Q)은 12번으로, 11번(Q')은 10번으로 되먹인다. Q와 Q'에는 각각 330Ω 저항과 LED를 달아 출력이 1일 때 켜지게 한다.
강의노트대로 첫 입력은 Set 또는 Reset이다. E=1에서 Reset(S=0, R=1)과 Set(S=1, R=0)을 먼저 넣어 Q가 0과 1로 정해지는지 보고, 그 뒤 S=R=0으로 바꾸고 다시 E=0으로 내려 앞 값이 그대로 남는지 확인한다. 부정 상태인 S=R=1은 마지막에 넣어 Q와 Q' 두 LED가 함께 켜지는지 본다.
- **SR Latch with Enable** (Q = ((S·E)'·Q')', Q' = ((E·R)'·Q)')
	<table header-row="true">
<tr>
<td>E</td>
<td>S</td>
<td>R</td>
<td>Q(t)</td>
</tr>
<tr>
<td>0</td>
<td>X</td>
<td>X</td>
<td>Q(t-1)</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>Q(t-1)</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0: Reset</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1: Set</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>X (부정)</td>
</tr>
	</table>
<empty-block/>
## 실험 2-1) D Latch with Enable
실험 1의 회로에서 R 입력 점퍼만 뽑고 74HC04를 더한다. S 자리였던 1번 입력이 이제 D가 되고, D를 74HC04의 1번에도 이어 그 출력 2번(D')을 74HC00의 5번에 넣는다. E 배선, 게이트 사이 배선, 두 LED는 그대로 둔다.
실험 1과 마찬가지로 E=1에서 D=0(Reset)과 D=1(Set)을 먼저 넣어 Q가 D를 따라가는지 보고, 그 뒤 E=0으로 내린 다음 D를 바꿔도 Q가 마지막 값을 유지하는지 확인한다. 어떤 입력에서도 Q와 Q' LED가 동시에 켜지지 않아야 한다.
- **D Latch with Enable** (Q = ((D·E)'·Q')', Q' = ((E·D')'·Q)')
	<table header-row="true">
<tr>
<td>E</td>
<td>D</td>
<td>Q(t)</td>
</tr>
<tr>
<td>0</td>
<td>X</td>
<td>Q(t-1)</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0: Reset</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1: Set</td>
</tr>
	</table>
<empty-block/>
## 실험 3-2) JK F/F – IC(74HC76) 활용
74HC76은 칩과 전원 핀 자리가 모두 달라, 전원을 끄고 레일을 잇는 선만 남긴 채 D Latch의 칩과 배선, LED를 모두 뽑은 뒤 새로 꽂는다. 1번 플립플롭의 CLK·SET·RESET·J·K(1·2·3·4·16번)에 입력 점퍼를 물리고, Q(15번)와 Q'(14번)에 330Ω 저항과 LED를 단다.
표의 순서대로 진행한다. 처음 두 행은 SET과 RESET 중 하나만 0으로 내려 클럭 없이 Q가 1 또는 0으로 정해지는지 본다. 셋째 행은 SET과 RESET을 모두 1로 두고 CLK를 0에 둔 채 J와 K를 바꿔도 Q가 변하지 않는지 확인한다. 이 세 행 동안 CLK는 줄곧 0에 둔다. 1에 두었다가 셋째 행에서 내리면 그 순간이 하강 에지가 되어 Q가 바뀐다. 나머지 네 행은 CLK를 1로 올리고 J와 K를 정한 다음 CLK를 0으로 내려 하강 에지 하나를 주고, Q가 유지·Reset·Set·토글로 바뀌는지 본다. 표의 CLK 칸에서 1-\>0은 이 하강 에지를 뜻한다.
- **JK F/F (74HC76)** (Q(t) = J·Q(t-1)' + K'·Q(t-1), 하강 에지에서)
	<table header-row="true">
<tr>
<td>Set</td>
<td>Reset</td>
<td>CLK</td>
<td>J</td>
<td>K</td>
<td>Q(t)</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>X</td>
<td>X</td>
<td>X</td>
<td>1: Set</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>X</td>
<td>X</td>
<td>X</td>
<td>0: Reset</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>X</td>
<td>X</td>
<td>Q(t-1)</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1-\>0</td>
<td>0</td>
<td>0</td>
<td>Q(t-1)</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1-\>0</td>
<td>0</td>
<td>1</td>
<td>0: Reset</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1-\>0</td>
<td>1</td>
<td>0</td>
<td>1: Set</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>Q(t-1)'</td>
</tr>
	</table>
<empty-block/>
<empty-block/>
# 회로 결선도
## 공통 결선 규칙
- 74HC00과 74HC04는 14번 핀을 +5V에, 7번 핀을 GND에 연결한다. 74HC76은 5번 핀을 +5V에, 13번 핀을 GND에 연결한다.
- 쓰는 게이트와 플립플롭의 입력은 점퍼선으로 +5V(=1) 또는 GND(=0)에 직접 물리고 띄워 두지 않는다. 74HC76의 하강 에지는 CLK 점퍼의 끝을 +5V 레일에서 GND 레일로 옮겨 꽂아 만든다.
- LED는 출력 Q와 Q'에 하나씩, 출력 핀에서 330Ω 저항을 거쳐 애노드로 들어가고 캐소드를 GND로 내린다. 출력이 1일 때 켜진다.
- 쓰지 않는 74HC04의 인버터 다섯 개와 74HC76의 2번 플립플롭은 입력과 출력을 모두 비워 둔다.
- 한 신호가 여러 핀으로 가면 첫 목적지 핀에서 다음 목적지로 이어 간다. 표에서 "같은 칩 4번 핀"처럼 적은 것이 그 이어 간 선이고, 전기적으로는 한 점이다. 래치의 되먹임 두 가닥도 칩 옆에서 바로 잇는다.
- 칩을 꽂거나 뽑을 때는 전원을 끈다.
<empty-block/>
## 실험 1) SR Latch with Enable 결선
![실험 1) SR Latch with Enable 브레드보드 작도]()
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>74HC00</td>
<td>1</td>
<td>입력 S</td>
</tr>
<tr>
<td>74HC00</td>
<td>2</td>
<td>입력 E, 같은 칩 4번 핀</td>
</tr>
<tr>
<td>74HC00</td>
<td>4</td>
<td>같은 칩 2번 핀 (E)</td>
</tr>
<tr>
<td>74HC00</td>
<td>5</td>
<td>입력 R</td>
</tr>
<tr>
<td>74HC00</td>
<td>3</td>
<td>같은 칩 9번 핀 ((S·E)')</td>
</tr>
<tr>
<td>74HC00</td>
<td>6</td>
<td>같은 칩 13번 핀 ((E·R)')</td>
</tr>
<tr>
<td>74HC00</td>
<td>9</td>
<td>같은 칩 3번 핀 ((S·E)')</td>
</tr>
<tr>
<td>74HC00</td>
<td>10</td>
<td>같은 칩 11번 핀 (Q')</td>
</tr>
<tr>
<td>74HC00</td>
<td>12</td>
<td>같은 칩 8번 핀 (Q)</td>
</tr>
<tr>
<td>74HC00</td>
<td>13</td>
<td>같은 칩 6번 핀 ((E·R)')</td>
</tr>
<tr>
<td>74HC00</td>
<td>8</td>
<td>같은 칩 12번 핀, 330Ω, LED Q</td>
</tr>
<tr>
<td>74HC00</td>
<td>11</td>
<td>같은 칩 10번 핀, 330Ω, LED Q'</td>
</tr>
</table>
<empty-block/>
## 실험 2-1) D Latch with Enable 결선
![실험 2-1) D Latch with Enable 브레드보드 작도]()
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>74HC00</td>
<td>1</td>
<td>입력 D, 74HC04의 1번 핀</td>
</tr>
<tr>
<td>74HC00</td>
<td>2</td>
<td>입력 E, 같은 칩 4번 핀</td>
</tr>
<tr>
<td>74HC00</td>
<td>4</td>
<td>같은 칩 2번 핀 (E)</td>
</tr>
<tr>
<td>74HC00</td>
<td>5</td>
<td>74HC04의 2번 핀 (D')</td>
</tr>
<tr>
<td>74HC00</td>
<td>3</td>
<td>같은 칩 9번 핀 ((D·E)')</td>
</tr>
<tr>
<td>74HC00</td>
<td>6</td>
<td>같은 칩 13번 핀 ((E·D')')</td>
</tr>
<tr>
<td>74HC00</td>
<td>9</td>
<td>같은 칩 3번 핀 ((D·E)')</td>
</tr>
<tr>
<td>74HC00</td>
<td>10</td>
<td>같은 칩 11번 핀 (Q')</td>
</tr>
<tr>
<td>74HC00</td>
<td>12</td>
<td>같은 칩 8번 핀 (Q)</td>
</tr>
<tr>
<td>74HC00</td>
<td>13</td>
<td>같은 칩 6번 핀 ((E·D')')</td>
</tr>
<tr>
<td>74HC00</td>
<td>8</td>
<td>같은 칩 12번 핀, 330Ω, LED Q</td>
</tr>
<tr>
<td>74HC00</td>
<td>11</td>
<td>같은 칩 10번 핀, 330Ω, LED Q'</td>
</tr>
<tr>
<td>74HC04</td>
<td>1</td>
<td>74HC00의 1번 핀 (D)</td>
</tr>
<tr>
<td>74HC04</td>
<td>2</td>
<td>74HC00의 5번 핀 (D')</td>
</tr>
<tr>
<td>74HC04</td>
<td>3, 5, 9, 11, 13</td>
<td>미연결</td>
</tr>
</table>
<empty-block/>
## 실험 3-2) JK F/F – IC(74HC76) 활용 결선
![실험 3-2) JK F/F 브레드보드 작도]()
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>74HC76</td>
<td>1</td>
<td>입력 CLK</td>
</tr>
<tr>
<td>74HC76</td>
<td>2</td>
<td>입력 SET</td>
</tr>
<tr>
<td>74HC76</td>
<td>3</td>
<td>입력 RESET</td>
</tr>
<tr>
<td>74HC76</td>
<td>4</td>
<td>입력 J</td>
</tr>
<tr>
<td>74HC76</td>
<td>16</td>
<td>입력 K</td>
</tr>
<tr>
<td>74HC76</td>
<td>15</td>
<td>330Ω, LED Q(t)</td>
</tr>
<tr>
<td>74HC76</td>
<td>14</td>
<td>330Ω, LED Q(t)'</td>
</tr>
<tr>
<td>74HC76</td>
<td>6, 7, 8, 9, 12</td>
<td>미연결</td>
</tr>
<tr>
<td>74HC76</td>
<td>10, 11</td>
<td>미연결</td>
</tr>
</table>
<empty-block/>
## 실험 전 확인할 사항
- 74HC76은 5번이 +5V, 13번이 GND다. 16번과 8번에 전원을 꽂지 않았는지 전원을 넣기 전에 다시 본다.
- 74HC76의 SET과 RESET을 동시에 0으로 내리는 조합은 강의노트 표에 없으니 넣지 않는다.
- 점퍼를 손으로 옮기면 접점이 튀어 에지가 여러 번 생길 수 있다. 유지·Set·Reset 행은 에지가 여러 번이어도 결과가 같지만, J=K=1 토글 행은 에지 수가 짝수면 Q가 그대로 남는다. 토글 행이 표와 다르면 같은 행을 몇 번 되풀이해 본다.
- 브레드보드에서 LED는 SR Latch와 D Latch에서는 위가 Q', 아래가 Q이고, JK F/F에서는 위가 Q(t), 아래가 Q(t)'이다. 기록하는 것은 Q 쪽이다.
- D Latch로 넘어갈 때 74HC00의 5번에 R 점퍼가 남아 있지 않은지 본다.
- Q와 Q'는 LED를 구동하면서 상대 게이트의 입력이기도 하다. 330Ω에서 LED 전류는 많아야 9mA 정도라 출력 전압이 5V보다 조금 내려갈 수 있다. 래치가 Set이나 Reset 뒤 값을 잡지 못하면 LED를 빼고 멀티미터로 Q를 찍어 본다.
- 74HC04의 남는 인버터와 74HC76의 2번 플립플롭은 입력을 비워 둔다. LED가 진리표와 어긋나면 이 자리도 확인하고, 1번 플립플롭이 동작하지 않으면 2번으로 옮겨 칩 문제인지 가린다.
- 강의노트 표의 회색 행(E=0 행, 74HC76 표의 앞 세 행)도 확인하고 기록한다.
- 강의노트 준비물에 IC 수량이 적혀 있지 않다. 74HC00, 74HC04, 74HC76을 각각 하나로 보고 배선했으니 지급된 수량을 먼저 확인한다.
- 74HC76의 각인을 확인한다. 참고한 데이터시트는 STMicroelectronics의 단종 제품 문서라, 다른 제조사 칩이면 그 제조사 데이터시트와 대조한다. 74HC가 아닌 74LS 계열이면 전기 특성이 다르다.
- 입력 스위치나 펄스 발생기, 오실로스코프 사용을 조교가 지시하면 그대로 따른다.
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트
- 논리회로실험 IC 특성 분석 가이드
- Nexperia. 74HC00; 74HCT00 — Quad 2-input NAND gate. Rev. 11, 2025-04-29.
	[https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf)
- Nexperia. 74HC04; 74HCT04 — Hex inverter. Rev. 10, 2024-02-16.
	[https://assets.nexperia.com/documents/data-sheet/74HC_HCT04.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT04.pdf)
- STMicroelectronics. M74HC76 — Dual J-K flip flop with preset and clear. 2001-08.
	[https://media.digikey.com/pdf/data%20sheets/st%20microelectronics%20pdfs/m74hc76.pdf](https://media.digikey.com/pdf/data%20sheets/st%20microelectronics%20pdfs/m74hc76.pdf)