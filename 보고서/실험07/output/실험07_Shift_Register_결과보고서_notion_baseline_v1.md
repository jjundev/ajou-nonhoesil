<table_of_contents color="gray"/>
<empty-block/>
# 실험 결과
## 6bit Shift Right Register
74HC00의 NAND 게이트와 74HC76의 JK 플립플롭 여섯 개로 직렬 입력을 BIT1부터 BIT6까지 이동시키는 회로를 구성했다. 각 출력에 연결한 LED가 켜지면 1, 꺼지면 0으로 기록했다.
- **초기화 및 직렬 입력 결과**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>D</td>
<td>CLK</td>
<td>CLR</td>
<td>PR1</td>
<td>PR2</td>
</tr>
<tr>
<td>R0</td>
<td>CLK 정지, 공통 초기화(p9)</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>R1</td>
<td>CLR 해제, 에지 없이 관찰</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S1</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>1</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S2</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S3</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>1</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S4</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>1</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S6</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **출력 상태**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>BIT1</td>
<td>BIT2</td>
<td>BIT3</td>
<td>BIT4</td>
<td>BIT5</td>
<td>BIT6</td>
</tr>
<tr>
<td>R0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S2</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S3</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S4</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S5</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>S6</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
	</table>
초기화와 여섯 번의 직렬 입력 결과는 예상과 일치했다. 첫 번째로 넣은 1은 여섯 번째 하강 에지 후 BIT6에 도달했다.
- **PR1 강제 SET 및 이동 결과**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>D</td>
<td>CLK</td>
<td>CLR</td>
<td>PR1</td>
<td>PR2</td>
</tr>
<tr>
<td>R0</td>
<td>CLK 정지, 재초기화</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>P1</td>
<td>먼저 CLR=1, 그다음 PR1=0. CLK=0 유지</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>P2</td>
<td>PR1을 1로 해제, 에지 없이 관찰</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S1</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S2</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S3</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S4</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S6</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **출력 상태**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>BIT1</td>
<td>BIT2</td>
<td>BIT3</td>
<td>BIT4</td>
<td>BIT5</td>
<td>BIT6</td>
</tr>
<tr>
<td>R0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>P1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>P2</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S2</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S3</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S4</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>S5</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>S6</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
PR1을 해제한 뒤 다섯 번째 하강 에지에서 1이 BIT6에 도달했고, 여섯 번째 에지 뒤에는 모든 LED가 꺼졌다.
- **PR2 강제 SET 및 이동 결과**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>D</td>
<td>CLK</td>
<td>CLR</td>
<td>PR1</td>
<td>PR2</td>
</tr>
<tr>
<td>R0</td>
<td>CLK 정지, 재초기화</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>P1</td>
<td>먼저 CLR=1, 그다음 PR2=0. CLK=0 유지</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>P2</td>
<td>PR2를 1로 해제, 에지 없이 관찰</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S1</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S2</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S3</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S4</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **출력 상태**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>BIT1</td>
<td>BIT2</td>
<td>BIT3</td>
<td>BIT4</td>
<td>BIT5</td>
<td>BIT6</td>
</tr>
<tr>
<td>R0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>P1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>P2</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S2</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S3</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>S4</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
PR2로 만든 1은 해제 후 네 번째 하강 에지에서 BIT6에 도달했고, 다섯 번째 에지 뒤에 빠져나갔다. 두 강제 SET 시험 모두 예상과 일치했다.
<empty-block/>
<empty-block/>
# 실험 사진
예비보고서에서 그린 결선도와 직렬 입력에 따른 LED 점등·소등 장면을 함께 실었다. 아래 사진은 위 표의 입력 순서와는 별도로 촬영한 동작 장면이다.
<empty-block/>
## 6bit Shift Right Register
![예비보고서에서 그린 6bit 시프트 레지스터 결선도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/3707502c-30cf-461e-913d-fe38e234d72d/%EC%8B%A4%ED%97%9807_1_%EC%86%90%EA%B7%B8%EB%A6%BC_6bit%EC%8B%9C%ED%94%84%ED%8A%B8%EB%A0%88%EC%A7%80%EC%8A%A4%ED%84%B0.png)
![직렬 입력을 1로 둔 뒤 LED가 점등되는 장면](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/738fe385-105a-4a1e-b2ec-a4ff801b9c0b/01_D1_%EC%84%A4%EB%AA%85_%ED%9B%84_LED_%EC%A0%90%EB%93%B1_%EC%A7%84%ED%96%89.png)
![직렬 입력을 0으로 바꾼 뒤 LED가 소등되는 장면](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/4f401d25-8b22-4751-bad6-7de4ce11ba8b/02_D0_%EB%B3%80%EA%B2%BD_%EC%A0%84%ED%9B%84_LED_%EC%83%81%ED%83%9C.png)
<empty-block/>
<empty-block/>
# 예비보고서와의 비교
공통 CLR로 초기화한 뒤 직렬 입력을 넣자 하강 에지마다 저장된 값이 한 단씩 이동했다. PR1과 PR2도 각각 해당 비트를 강제 SET하고 해제 후 그 값이 이동하여 예비보고서에서 예상한 동작과 일치했다.
<empty-block/>
<empty-block/>
# 결과 분석
첫 단은 J에 D를, K에 NAND 게이트로 반전한 D를 받는다. 나머지 단은 앞단의 Q와 Q'를 각각 J와 K에 받으므로 하강 에지마다 에지 직전 앞단의 값이 저장된다. 모든 단이 같은 클럭을 받아도 각 비트는 한 번에 한 단씩 이동한다.
PR1과 PR2는 각각 BIT1과 BIT2의 비동기 SET 입력이다. 클럭을 멈춘 상태에서도 해당 출력을 1로 만들며, 해제한 뒤에는 직렬 이동이 다시 가능하다.
처음에는 직렬 입력과 PR1 강제 주입을 시도해도 LED가 켜지지 않았다. LED를 따로 확인했을 때는 문제가 없었고, 첫 두 플립플롭이 들어 있는 U2가 제대로 꽂혀 있지 않은 것을 발견했다. U2를 다시 꽂은 뒤 두 방법에서 LED가 켜졌다. U2가 제대로 꽂히지 않아 회로가 동작하지 않았던 것으로 보인다.
<empty-block/>
<empty-block/>
# 고찰
초기화, 직렬 입력의 이동, PR1과 PR2의 강제 SET을 확인하여 시프트 레지스터의 동작을 이해하려는 실험 목적을 달성했다고 본다.
처음에 LED가 켜지지 않아 회로를 확인하는 데 막혔다. LED 자체에는 문제가 없었고, 결과 분석에서 살펴본 것처럼 U2를 다시 꽂은 뒤 정상적으로 점등했다.
<empty-block/>
<empty-block/>
# 추가 공부
## IC 삽입 상태와 순차회로의 확인
첫 단이 동작하지 않으면 뒤 단에 전달할 데이터도 생기지 않으므로 여러 LED가 함께 꺼져 있어도 모든 플립플롭이 불량이라고 판단할 수는 없다. 전원과 접지, IC 삽입 상태를 확인한 다음 첫 단의 입력과 출력을 살피고 뒤 단으로 범위를 넓히면 고장 지점을 좁힐 수 있다. 이번에는 제대로 꽂히지 않은 U2를 다시 꽂은 뒤 동작이 회복됐다.
<empty-block/>
## 출력 부하와 논리 레벨
BIT1\~BIT5의 Q 출력은 LED 회로와 다음 단의 J 입력을 함께 구동하고, 마지막 BIT6의 Q 출력은 LED 회로에 연결된다. LED에 흐르는 전류 때문에 출력 전압이 낮아지면 다음 단이 읽는 논리 레벨에도 영향을 줄 수 있다. 출력 전압과 전류의 보증 조건을 해당 제조사의 데이터시트에서 확인하고, 실제 회로의 부하 상태에서 전압을 측정해야 안정적인 동작 여유를 판단할 수 있다.
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트
- 논리회로실험 IC 특성 분석 가이드
- Nexperia. 74HC00; 74HCT00, Quad 2-input NAND gate. 문서번호 74HC_HCT00, Rev. 11, 2025-04-29. [https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf)
- Renesas Electronics. HD74HC76, Dual J-K Flip-Flops (with Preset and Clear). 문서번호 REJ03D0551-0200 (Previous ADE-205-423), Rev. 2.00, 2005-10-06. [https://www.renesas.com/en/document/dst/hd74hc76-datasheet](https://www.renesas.com/en/document/dst/hd74hc76-datasheet)