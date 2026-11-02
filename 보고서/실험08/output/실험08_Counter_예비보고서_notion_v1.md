<table_of_contents color="gray"/>
<empty-block/>
# 실험 목적
레지스터의 구성을 이해하고 카운터의 동작 원리와 특성을 익힌다. 먼저 JK 플립플롭 두 개로 2단 2진 비동기 카운터를 구성해 네 출력이 차례로 켜지는지 확인한다. 이어서 7490으로 BCD 카운터를 구성하고, 7447 디코더와 7-Segment 표시기를 연결해 카운터 값을 숫자로 표시한다.
<empty-block/>
<empty-block/>
# 실험 이론
## 레지스터와 카운터
n bit 레지스터는 n개의 플립플롭으로 구성되며 처리 중인 정보를 임시로 저장한다. 카운터는 클럭 펄스마다 현재 숫자를 갱신해 저장하는 레지스터다. 이번 실험의 두 회로는 이전 플립플롭의 출력이 다음 플립플롭의 클럭으로 전달되는 비동기식이다. 뒤 단은 앞 단이 바뀐 뒤에 바뀌므로 전송 지연이 발생한다.
<empty-block/>
## JK 플립플롭의 Toggle 동작
74HC76의 PR·CL은 Active Low 입력이므로 1로 고정하면 동작에 관여하지 않는다. 이때 다음 상태는 Q(next)=J·Q'+K'·Q이고, J=K=1이면 Q(next)=Q'가 된다. 플립플롭은 하강 에지마다 이전 출력을 뒤집는 T 플립플롭으로 동작한다.
<empty-block/>
## 2단 2진 카운터와 출력 조합
FFA는 CLK의 하강 에지에서, FFB는 A의 하강 에지에서 Toggle한다. A의 주기는 CLK의 2배, B의 주기는 CLK의 4배이므로 1Hz 클럭에서는 네 상태가 1s씩 이어진다. A를 앞에 적으면 AB는 00, 10, 01, 11 순서로 바뀌고, B를 높은 자리로 읽으면 0, 1, 2, 3이 된다. (강의노트 본문은 00, 01, 10, 11로 적었으나 파형과 회로도에 맞추면 A를 앞에 적은 순서는 00, 10, 01, 11이다.)
A가 1에서 0으로 떨어질 때는 B가 뒤따라 바뀌므로 10에서 01로 갈 때 00을, 11에서 00으로 갈 때 01을 잠깐 지난다. 이 짧은 구간이 비동기식의 전송 지연이다.
AND 게이트는 두 입력이 모두 1일 때만 1을 낸다. A, A', B, B'를 네 조합으로 연결하면 Y0=A'·B', Y1=A·B', Y2=A'·B, Y3=A·B가 되고, 네 상태마다 출력 하나만 1이다. Y0\~Y3은 강의노트 파형 옆의 출력 번호 0\~3을 가리킨다.
<empty-block/>
## BCD 카운터 7490
7490은 INPUT A로 동작하는 2분주 단(QA)과 INPUT B로 동작하는 5분주 단(QB, QC, QD)으로 나뉜다. 클럭을 INPUT A에 넣고 QA를 INPUT B에 연결하면 QA는 입력 하강 에지마다 뒤집히고, QA가 1에서 0으로 떨어질 때마다 뒷단이 한 칸 진행한다. 뒷단이 0\~4를 세므로 COUNT는 (QD QC QB의 값)×2+QA가 되어 0부터 9까지 센 뒤 0으로 돌아간다.
R0(1)·R0(2)가 모두 H이면 출력은 0으로, R9(1)·R9(2)가 모두 H이면 9로 고정되며 R9가 우선한다. 이번 회로는 R9 두 핀을 GND에 고정하고 R0 두 핀을 묶어 R0 하나로 조작한다. 그래서 R0=1이면 0을 유지하고 R0=0이면 카운트한다. 아래 표의 X는 don't care다.
- **Truth Table - COUNT**
	<table header-row="true">
<tr>
<td>COUNT</td>
<td>QD</td>
<td>QC</td>
<td>QB</td>
<td>QA</td>
</tr>
<tr>
<td>0</td>
<td>L</td>
<td>L</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>1</td>
<td>L</td>
<td>L</td>
<td>L</td>
<td>H</td>
</tr>
<tr>
<td>2</td>
<td>L</td>
<td>L</td>
<td>H</td>
<td>L</td>
</tr>
<tr>
<td>3</td>
<td>L</td>
<td>L</td>
<td>H</td>
<td>H</td>
</tr>
<tr>
<td>4</td>
<td>L</td>
<td>H</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>5</td>
<td>L</td>
<td>H</td>
<td>L</td>
<td>H</td>
</tr>
<tr>
<td>6</td>
<td>L</td>
<td>H</td>
<td>H</td>
<td>L</td>
</tr>
<tr>
<td>7</td>
<td>L</td>
<td>H</td>
<td>H</td>
<td>H</td>
</tr>
<tr>
<td>8</td>
<td>H</td>
<td>L</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>9</td>
<td>H</td>
<td>L</td>
<td>L</td>
<td>H</td>
</tr>
	</table>
- **Truth Table - Reset**
	<table header-row="true">
<tr>
<td>R0(1)</td>
<td>R0(2)</td>
<td>R9(1)</td>
<td>R9(2)</td>
<td>QD</td>
<td>QC</td>
<td>QB</td>
<td>QA</td>
</tr>
<tr>
<td>H</td>
<td>H</td>
<td>L</td>
<td>X</td>
<td>L</td>
<td>L</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>H</td>
<td>H</td>
<td>X</td>
<td>L</td>
<td>L</td>
<td>L</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>X</td>
<td>X</td>
<td>H</td>
<td>H</td>
<td>H</td>
<td>L</td>
<td>L</td>
<td>H</td>
</tr>
<tr>
<td>X</td>
<td>L</td>
<td>X</td>
<td>L</td>
<td>COUNT</td>
<td>COUNT</td>
<td>COUNT</td>
<td>COUNT</td>
</tr>
<tr>
<td>X</td>
<td>L</td>
<td>L</td>
<td>X</td>
<td>COUNT</td>
<td>COUNT</td>
<td>COUNT</td>
<td>COUNT</td>
</tr>
<tr>
<td>L</td>
<td>X</td>
<td>X</td>
<td>L</td>
<td>COUNT</td>
<td>COUNT</td>
<td>COUNT</td>
<td>COUNT</td>
</tr>
<tr>
<td>L</td>
<td>X</td>
<td>L</td>
<td>X</td>
<td>COUNT</td>
<td>COUNT</td>
<td>COUNT</td>
<td>COUNT</td>
</tr>
	</table>
<empty-block/>
## 7447 디코더와 7-Segment 표시기
7447은 0\~9의 4bit 이진수를 입력받아 세그먼트 구동 신호 a\~g로 변환한다. 출력은 Active Low 오픈 컬렉터로, 세그먼트를 켤 때 0으로 내려가 전류를 받아들인다. SN7447A의 싱크 전류는 40mA, 출력 최대 전압은 15V다.
FND 507은 Common Anode 표시기다. 공통 단자 3번과 8번에 +5V를 주고 세그먼트 핀을 330Ω을 거쳐 7447 출력에 연결하면, 출력이 0인 세그먼트만 켜진다. Common Cathode 표시기는 이 회로에서 동작하지 않는다.
제어 입력은 0일 때 동작한다. /LT는 모든 세그먼트를 켜고, /BI는 모두 끄며, /RBI는 입력이 0일 때 공백으로 처리한다. 숫자를 그대로 표시하려면 세 핀을 모두 1로 둔다.
<empty-block/>
<empty-block/>
# 실험 부품
## 준비물
<table header-row="true">
<tr>
<td>부품·장비</td>
<td>수량</td>
<td>용도</td>
</tr>
<tr>
<td>5V 전압원</td>
<td>1대</td>
<td>IC와 논리 입력의 전원</td>
</tr>
<tr>
<td>오실로스코프</td>
<td>1대</td>
<td>클럭 파형과 신호 레벨 확인</td>
</tr>
<tr>
<td>클럭 발생 장비</td>
<td>1대</td>
<td>0\~5V, 1Hz 클럭 공급</td>
</tr>
<tr>
<td>74HC76</td>
<td>1개</td>
<td>JK 플립플롭 두 개로 2단 카운터 구성</td>
</tr>
<tr>
<td>74HC08</td>
<td>1개</td>
<td>AND 게이트 네 개로 AB 조합 출력</td>
</tr>
<tr>
<td>7490</td>
<td>1개</td>
<td>BCD 카운터</td>
</tr>
<tr>
<td>7447</td>
<td>1개</td>
<td>BCD to 7-Segment 디코더</td>
</tr>
<tr>
<td>FND 507</td>
<td>1개</td>
<td>Common Anode 7-Segment 표시기</td>
</tr>
<tr>
<td>발광 다이오드</td>
<td>4개</td>
<td>Y0\~Y3와 A\~D 표시</td>
</tr>
<tr>
<td>330Ω 저항</td>
<td>11개</td>
<td>LED용 4개, 세그먼트용 7개</td>
</tr>
<tr>
<td>브레드보드</td>
<td>1개</td>
<td>회로 구성</td>
</tr>
<tr>
<td>점퍼선</td>
<td>필요량</td>
<td>신호 연결, R0과 입력 레벨 설정</td>
</tr>
</table>
<empty-block/>
## IC 구성과 핀 배치
<table header-row="true">
<tr>
<td>IC</td>
<td>내부 구성</td>
<td>입력 핀</td>
<td>출력 핀</td>
<td>VCC</td>
<td>GND</td>
</tr>
<tr>
<td>74HC76</td>
<td>JK F/F 1</td>
<td>CLK 1, PR 2, CL 3, J 4, K 16</td>
<td>Q 15, Q' 14</td>
<td>5</td>
<td>13</td>
</tr>
<tr>
<td>74HC76</td>
<td>JK F/F 2</td>
<td>CLK 6, PR 7, CL 8, J 9, K 12</td>
<td>Q 11, Q' 10</td>
<td>5</td>
<td>13</td>
</tr>
<tr>
<td>74HC08</td>
<td>2입력 AND 4개</td>
<td>1·2 / 4·5 / 9·10 / 12·13</td>
<td>3 / 6 / 8 / 11</td>
<td>14</td>
<td>7</td>
</tr>
<tr>
<td>7490</td>
<td>2분주 + 5분주 카운터</td>
<td>INPUT A 14, INPUT B 1, R0 2·3, R9 6·7</td>
<td>QA 12, QB 9, QC 8, QD 11</td>
<td>5</td>
<td>10</td>
</tr>
<tr>
<td>7447</td>
<td>BCD to 7-Segment 디코더</td>
<td>A 7, B 1, C 2, D 6, /LT 3, /BI·/RBO 4, /RBI 5</td>
<td>a 13, b 12, c 11, d 10, e 9, f 15, g 14</td>
<td>16</td>
<td>8</td>
</tr>
<tr>
<td>FND 507</td>
<td>Common Anode 표시기</td>
<td>A 7, B 6, C 4, D 2, E 1, F 9, G 10, DP 5</td>
<td>없음</td>
<td>3, 8</td>
<td>없음</td>
</tr>
</table>
<empty-block/>
<empty-block/>
# 실험 과정 및 예상 결과
## 실험 1) 2단 2진 카운터 (비동기)
74HC76 두 플립플롭의 J·K·PR·CL을 모두 VCC에 고정하고, A를 FFB의 CLK에 연결한다. AB의 네 조합을 74HC08의 네 게이트에 연결한 뒤 각 출력에 LED와 330Ω 저항을 직렬로 잇고, FFA의 CLK에 1Hz 클럭을 넣는다.
LED가 Y0, Y1, Y2, Y3 순서로 1s씩 켜지고 다시 Y0으로 돌아오면 정상이다. 회로에 초기화 입력이 없어 전원 직후의 AB는 정해지지 않으므로, Y0이 켜진 구간을 기준으로 잡고 그 뒤 순서를 대조한다. 표의 1은 LED가 켜진 상태, RUN은 클럭을 계속 넣는 상태다.
- **2단 2진 카운터 출력 순서** (Y0 = A'·B', Y1 = A·B', Y2 = A'·B, Y3 = A·B)
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>CLK</td>
<td>Y0</td>
<td>Y1</td>
<td>Y2</td>
<td>Y3</td>
</tr>
<tr>
<td>S1</td>
<td>전원과 발생기를 켠다. AB=00 구간. Y0이 켜진 때를 기준으로 잡는다</td>
<td>RUN</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S2</td>
<td>AB=10 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S3</td>
<td>AB=01 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>S4</td>
<td>AB=11 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>AB=00 구간으로 복귀</td>
<td>RUN</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
<empty-block/>
## 실험 3) 7-Segment 표시기를 갖는 BCD 카운터
먼저 BCD Counter를 구성한다. 클럭을 INPUT A에 넣고 QA를 INPUT B로 되돌리며, R9 두 핀은 GND에 잇는다. 출력 QA\~QD를 A\~D로 하여 LED와 330Ω 저항을 연결한다. R0는 묶은 두 핀을 점퍼로 +5V 또는 GND에 물려 조작한다. R0=1인 동안 클럭이 돌아도 0을 유지하는지 본 뒤 R0을 0으로 내린다. 표의 각 행은 그 값이 보이는 구간이며, 해제 뒤 첫 하강 에지의 시점은 맞추지 않는다.
- **BCD Counter 출력** (COUNT = (QD QC QB의 값)×2 + QA)
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>CLK</td>
<td>R0</td>
<td>A</td>
<td>B</td>
<td>C</td>
<td>D</td>
</tr>
<tr>
<td>R1</td>
<td>R0 점퍼를 +5V에 꽂고 전원과 발생기를 켠다. 클럭이 돌아도 0을 유지하는지 본다</td>
<td>RUN</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N1</td>
<td>R0 점퍼를 GND로 옮긴 뒤 COUNT 1 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N2</td>
<td>COUNT 2 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N3</td>
<td>COUNT 3 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N4</td>
<td>COUNT 4 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>N5</td>
<td>COUNT 5 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>N6</td>
<td>COUNT 6 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>N7</td>
<td>COUNT 7 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>N8</td>
<td>COUNT 8 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>N9</td>
<td>COUNT 9 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>N0</td>
<td>COUNT 0으로 복귀</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
다음으로 FND가 Common Anode인지 테스트한다. 7447을 꽂기 전에 FND의 3번과 8번을 VCC에 잇고 세그먼트 핀마다 330Ω을 연결한다. 전원을 켜고 GND에 물린 시험선을 저항의 빈 끝에 차례로 대어 해당 세그먼트만 켜지는지 확인한다. 표의 Segment A\~G는 세그먼트 a\~g이며, 7447 입력 A\~D와는 다른 이름이다. 켜지지 않는 행이 있으면 극성과 핀 번호, 접촉을 확인하고 다음 단계로 넘어가지 않는다.
- **FND 507 Common Anode 테스트**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>FND 핀</td>
<td>예상 세그먼트</td>
<td>실제 세그먼트</td>
</tr>
<tr>
<td>F1</td>
<td>pin 7의 330Ω 끝을 GND에 댄다</td>
<td>7</td>
<td>Segment A</td>
<td></td>
</tr>
<tr>
<td>F2</td>
<td>pin 6의 330Ω 끝을 GND에 댄다</td>
<td>6</td>
<td>Segment B</td>
<td></td>
</tr>
<tr>
<td>F3</td>
<td>pin 4의 330Ω 끝을 GND에 댄다</td>
<td>4</td>
<td>Segment C</td>
<td></td>
</tr>
<tr>
<td>F4</td>
<td>pin 2의 330Ω 끝을 GND에 댄다</td>
<td>2</td>
<td>Segment D</td>
<td></td>
</tr>
<tr>
<td>F5</td>
<td>pin 1의 330Ω 끝을 GND에 댄다</td>
<td>1</td>
<td>Segment E</td>
<td></td>
</tr>
<tr>
<td>F6</td>
<td>pin 9의 330Ω 끝을 GND에 댄다</td>
<td>9</td>
<td>Segment F</td>
<td></td>
</tr>
<tr>
<td>F7</td>
<td>pin 10의 330Ω 끝을 GND에 댄다</td>
<td>10</td>
<td>Segment G</td>
<td></td>
</tr>
	</table>
이어서 BCD to 7-Segment 표시기를 구성한다. 7447의 /LT, /BI, /RBI를 VCC에 잇고 a\~g 출력을 앞서 연결한 330Ω에 이은 뒤, 입력 D, C, B, A를 점퍼로 +5V 또는 GND에 물려 표의 값을 차례로 넣는다. 이 표의 A\~D는 7447의 입력이다. (강의노트 표 머리는 Input (DBCA)로 되어 있으나 0010이 숫자 2, 0100이 숫자 4이므로 값은 D, C, B, A 순서로 읽는다.) 켜지는 세그먼트 열은 강의노트의 입출력 표를 옮긴 것이다.
- **BCD to 7-Segment 입출력**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>D</td>
<td>C</td>
<td>B</td>
<td>A</td>
<td>켜지는 세그먼트</td>
<td>예상 숫자</td>
<td>실제 숫자</td>
</tr>
<tr>
<td>I0</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>abcdef</td>
<td>0</td>
<td></td>
</tr>
<tr>
<td>I1</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>bc</td>
<td>1</td>
<td></td>
</tr>
<tr>
<td>I2</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>abdeg</td>
<td>2</td>
<td></td>
</tr>
<tr>
<td>I3</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>abcdg</td>
<td>3</td>
<td></td>
</tr>
<tr>
<td>I4</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>bcfg</td>
<td>4</td>
<td></td>
</tr>
<tr>
<td>I5</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>acdfg</td>
<td>5</td>
<td></td>
</tr>
<tr>
<td>I6</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>cdefg</td>
<td>6</td>
<td></td>
</tr>
<tr>
<td>I7</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>abc</td>
<td>7</td>
<td></td>
</tr>
<tr>
<td>I8</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>abcdefg</td>
<td>8</td>
<td></td>
</tr>
<tr>
<td>I9</td>
<td>입력 점퍼를 표대로 옮기고 d 세그먼트가 켜졌는지도 본다</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>abcdfg</td>
<td>9</td>
<td></td>
</tr>
	</table>
마지막으로 입력 고정선을 뽑고 BCD Counter의 출력 A\~D를 7447의 입력 A\~D에 연결한다. A·B·C를 먼저 옮기고 D의 고정선은 끝까지 남겨 입력이 뜨지 않게 한다. R0=1에서 숫자 0을 확인한 뒤 R0을 내리면 FND가 1s마다 1부터 9까지 바뀌고 0으로 돌아온다.
- **7-Segment 표시기를 갖는 BCD 카운터**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>CLK</td>
<td>R0</td>
<td>예상 숫자</td>
<td>실제 숫자</td>
</tr>
<tr>
<td>R1</td>
<td>전원을 끄고 최종 결선을 마친 뒤 R0 점퍼를 +5V에 꽂고 전원과 발생기를 켠다. 클럭이 돌아도 0을 유지하는지 본다</td>
<td>RUN</td>
<td>1</td>
<td>0</td>
<td></td>
</tr>
<tr>
<td>N1</td>
<td>R0 점퍼를 GND로 옮긴 뒤 COUNT 1 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td></td>
</tr>
<tr>
<td>N2</td>
<td>COUNT 2 구간</td>
<td>RUN</td>
<td>0</td>
<td>2</td>
<td></td>
</tr>
<tr>
<td>N3</td>
<td>COUNT 3 구간</td>
<td>RUN</td>
<td>0</td>
<td>3</td>
<td></td>
</tr>
<tr>
<td>N4</td>
<td>COUNT 4 구간</td>
<td>RUN</td>
<td>0</td>
<td>4</td>
<td></td>
</tr>
<tr>
<td>N5</td>
<td>COUNT 5 구간</td>
<td>RUN</td>
<td>0</td>
<td>5</td>
<td></td>
</tr>
<tr>
<td>N6</td>
<td>COUNT 6 구간</td>
<td>RUN</td>
<td>0</td>
<td>6</td>
<td></td>
</tr>
<tr>
<td>N7</td>
<td>COUNT 7 구간</td>
<td>RUN</td>
<td>0</td>
<td>7</td>
<td></td>
</tr>
<tr>
<td>N8</td>
<td>COUNT 8 구간</td>
<td>RUN</td>
<td>0</td>
<td>8</td>
<td></td>
</tr>
<tr>
<td>N9</td>
<td>COUNT 9 구간. d 세그먼트가 켜졌는지도 본다</td>
<td>RUN</td>
<td>0</td>
<td>9</td>
<td></td>
</tr>
<tr>
<td>N0</td>
<td>COUNT 0으로 복귀</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td></td>
</tr>
	</table>
<empty-block/>
<empty-block/>
# 회로 결선도
## 공통 결선 규칙
실험 1의 U1은 74HC76, U2는 74HC08이다. 실험 3의 U1은 7490, U2는 7447, U3는 FND 507이다. 전원핀은 칩마다 다르므로 실험 부품 절의 핀 배치대로 잇는다. 칩을 꽂거나 배선을 바꿀 때는 전원과 발생기 출력을 끄고, 발생기·오실로스코프·회로의 GND는 공통으로 잇는다. 측정 중에 R0과 7447 입력 점퍼를 레일 사이로 옮기는 조작은 전원을 켠 채 한다.
LED 표시 회로는 출력 → LED → 330Ω → GND로 구성해 출력이 1일 때 켠다. 실험 1 회로는 전부 뽑고 실험 3을 새로 구성하며, 실험 3의 네 회로는 앞 회로 위에 차례로 이어 짓는다. 강의노트 회로도는 AND 네 개를 모두 1·2→3번으로 적었으므로 한 패키지의 네 게이트로 나누어 Y0은 12·13→11번, Y1은 1·2→3번, Y2는 4·5→6번, Y3은 9·10→8번을 쓴다. 최종 회로의 7490 출력 네 선은 LED 신호선과 같은 스트립에서 7447 입력으로 간다.
<empty-block/>
## 실험 1) 2단 2진 카운터 (비동기) 결선
![실험 1) 2단 2진 카운터 (비동기) 브레드보드 작도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/e9e44d13-102a-4987-99ff-91e37ad12768/0dd36187-f444-4973-b457-9c341e0a73c0.png)
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>기능</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>5</td>
<td>VCC(+5V)</td>
<td>전원</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>13</td>
<td>GND</td>
<td>접지</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>1</td>
<td>CLK</td>
<td>FFA CLK</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>2</td>
<td>VCC(+5V)</td>
<td>FFA PR</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>3</td>
<td>VCC(+5V)</td>
<td>FFA CL</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>4</td>
<td>VCC(+5V)</td>
<td>FFA J</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>16</td>
<td>VCC(+5V)</td>
<td>FFA K</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>15</td>
<td>[U1.pin](http://U1.pin)6, [U2.pin](http://U2.pin)9</td>
<td>A</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>14</td>
<td>[U2.pin](http://U2.pin)13</td>
<td>A'</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>6</td>
<td>[U1.pin](http://U1.pin)15</td>
<td>FFB CLK</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>7</td>
<td>VCC(+5V)</td>
<td>FFB PR</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>8</td>
<td>VCC(+5V)</td>
<td>FFB CL</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>9</td>
<td>VCC(+5V)</td>
<td>FFB J</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>12</td>
<td>VCC(+5V)</td>
<td>FFB K</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>11</td>
<td>[U2.pin](http://U2.pin)10</td>
<td>B</td>
</tr>
<tr>
<td>U1 (74HC76)</td>
<td>10</td>
<td>[U2.pin](http://U2.pin)12</td>
<td>B'</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>14</td>
<td>VCC(+5V)</td>
<td>전원</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>7</td>
<td>GND</td>
<td>접지</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>13</td>
<td>[U1.pin](http://U1.pin)14, [U2.pin](http://U2.pin)4</td>
<td>A'</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>12</td>
<td>[U1.pin](http://U1.pin)10, [U2.pin](http://U2.pin)2</td>
<td>B'</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>11</td>
<td>LED Y0 급전</td>
<td>Y0 = A'·B'</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>1</td>
<td>[U2.pin](http://U2.pin)9</td>
<td>A</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>2</td>
<td>[U2.pin](http://U2.pin)12</td>
<td>B'</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>3</td>
<td>LED Y1 급전</td>
<td>Y1 = A·B'</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>4</td>
<td>[U2.pin](http://U2.pin)13</td>
<td>A'</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>5</td>
<td>[U2.pin](http://U2.pin)10</td>
<td>B</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>6</td>
<td>LED Y2 급전</td>
<td>Y2 = A'·B</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>9</td>
<td>[U1.pin](http://U1.pin)15, [U2.pin](http://U2.pin)1</td>
<td>A</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>10</td>
<td>[U1.pin](http://U1.pin)11, [U2.pin](http://U2.pin)5</td>
<td>B</td>
</tr>
<tr>
<td>U2 (74HC08)</td>
<td>8</td>
<td>LED Y3 급전</td>
<td>Y3 = A·B</td>
</tr>
</table>
<empty-block/>
## 실험 3) 7-Segment 표시기를 갖는 BCD 카운터 결선
![실험 3) BCD Counter 브레드보드 작도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/b6508584-976d-462e-9f95-ad6ed058e4b2/b7c83090-c068-4c68-8e64-5c50fb4fe977.png)
- **BCD Counter**
	<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>기능</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>5</td>
<td>VCC(+5V)</td>
<td>전원</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>10</td>
<td>GND</td>
<td>접지</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>14</td>
<td>CLK</td>
<td>INPUT A</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>1</td>
<td>[U1.pin](http://U1.pin)12</td>
<td>INPUT B</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>2</td>
<td>R0, [U1.pin](http://U1.pin)3</td>
<td>R0(1)</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>3</td>
<td>[U1.pin](http://U1.pin)2</td>
<td>R0(2)</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>6</td>
<td>GND</td>
<td>R9(1)</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>7</td>
<td>GND</td>
<td>R9(2)</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>12</td>
<td>[U1.pin](http://U1.pin)1, LED A 급전</td>
<td>QA</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>9</td>
<td>LED B 급전</td>
<td>QB</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>8</td>
<td>LED C 급전</td>
<td>QC</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>11</td>
<td>LED D 급전</td>
<td>QD</td>
</tr>
<tr>
<td>U1 (7490)</td>
<td>미사용 4, 13</td>
<td>연결하지 않음</td>
<td>No Connect</td>
</tr>
	</table>
- **FND Common Anode 테스트**
	<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>기능</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>3</td>
<td>VCC(+5V)</td>
<td>Common Anode</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>8</td>
<td>VCC(+5V)</td>
<td>Common Anode</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>5</td>
<td>VCC(+5V)</td>
<td>Decimal Point</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>7</td>
<td>330Ω</td>
<td>Segment A</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>6</td>
<td>330Ω</td>
<td>Segment B</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>4</td>
<td>330Ω</td>
<td>Segment C</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>2</td>
<td>330Ω</td>
<td>Segment D</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>1</td>
<td>330Ω</td>
<td>Segment E</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>9</td>
<td>330Ω</td>
<td>Segment F</td>
</tr>
<tr>
<td>U3 (FND 507)</td>
<td>10</td>
<td>330Ω</td>
<td>Segment G</td>
</tr>
	</table>
- **BCD to 7-Segment 표시기**
	<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>기능</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>16</td>
<td>VCC(+5V)</td>
<td>전원</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>8</td>
<td>GND</td>
<td>접지</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>3</td>
<td>VCC(+5V)</td>
<td>/LT</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>4</td>
<td>VCC(+5V)</td>
<td>/BI·/RBO</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>5</td>
<td>VCC(+5V)</td>
<td>/RBI</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>7</td>
<td>+5V 또는 GND</td>
<td>A</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>1</td>
<td>+5V 또는 GND</td>
<td>B</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>2</td>
<td>+5V 또는 GND</td>
<td>C</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>6</td>
<td>+5V 또는 GND</td>
<td>D</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>13</td>
<td>330Ω → [U3.pin](http://U3.pin)7</td>
<td>a</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>12</td>
<td>330Ω → [U3.pin](http://U3.pin)6</td>
<td>b</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>11</td>
<td>330Ω → [U3.pin](http://U3.pin)4</td>
<td>c</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>10</td>
<td>330Ω → [U3.pin](http://U3.pin)2</td>
<td>d</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>9</td>
<td>330Ω → [U3.pin](http://U3.pin)1</td>
<td>e</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>15</td>
<td>330Ω → [U3.pin](http://U3.pin)9</td>
<td>f</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>14</td>
<td>330Ω → [U3.pin](http://U3.pin)10</td>
<td>g</td>
</tr>
	</table>
- **최종 BCD 카운터** (앞 회로에서 바뀌는 핀)
	<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>기능</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>7</td>
<td>[U1.pin](http://U1.pin)12 (7490 QA)</td>
<td>A</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>1</td>
<td>[U1.pin](http://U1.pin)9 (7490 QB)</td>
<td>B</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>2</td>
<td>[U1.pin](http://U1.pin)8 (7490 QC)</td>
<td>C</td>
</tr>
<tr>
<td>U2 (7447)</td>
<td>6</td>
<td>[U1.pin](http://U1.pin)11 (7490 QD)</td>
<td>D</td>
</tr>
	</table>
<empty-block/>
## 실험 전 확인할 사항
- 강의노트의 7490 핀맵은 6번·7번을 No Connect로 적었으나 내부 회로와 BCD Counter 회로도, 제조사 데이터시트는 이 두 핀을 R9로 쓴다. 입력이 뜨지 않도록 GND에 잇는다.
- 강의노트의 표시기 회로도는 FND 핀 번호가 Appendix 핀표와 다르다. 그림대로 꽂으면 3번 Anode에 d 신호가 가고 1번 E가 VCC에 묶이므로 Appendix의 FND 507 핀표대로 결선한다. 표시기 이름도 FND 205와 FND 507로 갈리므로 수령한 실물의 각인과 Common Anode 여부를 테스트 단계에서 확인한다.
- 강의노트의 입출력 표는 숫자 9를 abcdfg로 적었으나 SN7447A 데이터시트의 동작표에서 9는 a·b·c·f·g만 켜지고 d가 꺼진다. 예상 표는 강의노트대로 두고, 실험에서는 d 세그먼트의 상태까지 본다.
- 7490과 7447은 강의노트에서 DM7490A·74HC90, SN7447A·74HC47로 표기가 갈린다. 수령한 칩의 각인을 보고 해당 제조사 자료로 핀과 입력 조건을 대조한다. 74HC76도 VCC가 5번, GND가 13번인지 실물과 대조한다.
- 강의노트 준비물의 330Ω은 4개지만 LED 4개와 세그먼트 7개에 11개가 필요하다. 키트 수량을 미리 세고, 모자라면 LED 표시 회로의 저항을 세그먼트로 돌린다. 이 경우 최종 회로의 LED 확인은 생략되며 7개 미만이면 추가로 받아야 한다.
- 강의노트 회로도의 스위치 D0는 준비물에 없어 R0 점퍼로 대신한다. 실험실에 스위치가 있으면 회로도대로 쓴다.
- 발생기는 +5V, 1Hz로만 지정되어 있다. 회로에 잇기 전에 사각파 0\~+5V, 주기 1s인지 오실로스코프로 확인한다. 오프셋 +2.5V, 진폭 5Vpp를 설정 예로 쓰되 장비의 표시 단위와 부하 설정을 현장에서 확인한다. 파형 제출이 필요한지도 조교에게 확인한다.
- 7490 출력은 LED를 구동하면서 QA는 INPUT B도, 최종 회로의 네 출력은 7447 입력도 함께 구동한다. 카운트가 표와 다르면 해당 출력의 레벨을 오실로스코프로 보고, LED만 뽑아 다시 확인한다. 최종 회로에서는 LED 급전선이 7447 입력까지 이어지므로 급전선은 남긴다.
- 7447 입력 점퍼는 입출력 표를 마친 뒤 모두 GND 자리로 돌려놓고 최종 회로 결선을 시작한다. FND는 보드 골을 걸쳐 꽂으므로 몸통이 덮는 열과 다리 위치를 실물로 확인한다.
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트
- 논리회로실험 IC 특성 분석 가이드
- Renesas Electronics. HD74HC76, Dual J-K Flip-Flops (with Preset and Clear). 문서번호 REJ03D0551-0200 (Previous ADE-205-423), Rev. 2.00, 2005-10-06. [https://www.renesas.com/en/document/dst/hd74hc76-datasheet](https://www.renesas.com/en/document/dst/hd74hc76-datasheet)
- Texas Instruments. SN74HC08, SN54HC08, Quadruple 2-Input AND Gates. 문서번호 SCLS081J, 1982-12 발행, 2025-02 개정. [https://www.ti.com/lit/ds/symlink/sn74hc08.pdf](https://www.ti.com/lit/ds/symlink/sn74hc08.pdf)
- Texas Instruments. SN7490A, SN74LS90, Decade, Divide-by-Twelve and Binary Counters. 문서번호 SDLS940A, 1974-03 발행, 1988-03 개정. [https://www.ti.com/lit/ds/symlink/sn74ls90.pdf](https://www.ti.com/lit/ds/symlink/sn74ls90.pdf)
- Texas Instruments. SN7447A, SN74LS47, BCD-to-Seven-Segment Decoders/Drivers. 문서번호 SDLS111, 1974-03 발행, 1988-03 개정. [https://www.ti.com/lit/ds/symlink/sn74ls47.pdf](https://www.ti.com/lit/ds/symlink/sn74ls47.pdf)